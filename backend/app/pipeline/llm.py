import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger("paperproof.llm")


class GeminiClientWrapper:
    """
    Async wrapper around google-genai SDK with:
    - Automatic detection of standard Gemini API keys vs Vertex Express (AQ.*) keys
    - JSON response enforcement and safe markdown fence stripping
    - Retry with exponential backoff for 429 / transient errors
    - Graceful degradation to heuristic mode on failure or missing key
    """

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._available: Optional[bool] = None
        self._model_name = self.settings.gemini_model or "gemini-3.5-flash-lite"
        self._fallback_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]
        self._semaphore = asyncio.Semaphore(5)

    def _build_client(self):
        api_key = (self.settings.gemini_api_key or "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            return None
        try:
            from google import genai
            from google.genai import types
            return genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=25000),
            )
        except Exception as exc:
            logger.warning("Failed to initialize google-genai client: %s", exc)
            return None

    @property
    def is_configured(self) -> bool:
        api_key = (self.settings.gemini_api_key or "").strip()
        return bool(api_key and api_key != "your_gemini_api_key_here")

    def _extract_json(self, raw_text: str) -> Any:
        text = (raw_text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the outermost JSON object or array
            obj_start = text.find("{")
            arr_start = text.find("[")
            starts = [i for i in (obj_start, arr_start) if i != -1]
            if not starts:
                raise
            start = min(starts)
            end = text.rfind("}") if text[start] == "{" else text.rfind("]")
            if end > start:
                return json.loads(text[start : end + 1])
            raise

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Optional[Any]:
        if not self.is_configured:
            return None

        if self._client is None:
            self._client = self._build_client()
            if self._client is None:
                return None

        from google.genai import types

        models_to_try = [self._model_name] + [
            m for m in self._fallback_models if m != self._model_name
        ]

        async with self._semaphore:
            for model_name in models_to_try:
                for attempt in range(3):
                    try:
                        def _call():
                            config = types.GenerateContentConfig(
                                temperature=temperature,
                                response_mime_type="application/json",
                                system_instruction=system_instruction,
                            )
                            return self._client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=config,
                            )

                        response = await asyncio.to_thread(_call)
                        raw_text = getattr(response, "text", None) or ""
                        if not raw_text and getattr(response, "candidates", None):
                            parts = response.candidates[0].content.parts
                            raw_text = "".join(getattr(p, "text", "") for p in parts)

                        parsed = self._extract_json(raw_text)
                        self._model_name = model_name
                        self._available = True
                        return parsed
                    except Exception as exc:
                        msg = str(exc).lower()
                        if "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate" in msg:
                            await asyncio.sleep(1.5 * (2 ** attempt))
                            continue
                        if "not found" in msg or "404" in msg or "unsupported" in msg:
                            logger.info("Model %s unavailable, trying next model...", model_name)
                            break
                        if "api_key" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
                            # If AQ key failed with vertexai=True, try standard client once
                            if (self.settings.gemini_api_key or "").startswith("AQ."):
                                try:
                                    from google import genai
                                    alt_client = genai.Client(api_key=self.settings.gemini_api_key.strip())
                                    self._client = alt_client
                                    continue
                                except Exception:
                                    pass
                            logger.warning("Gemini authentication failed (%s); falling back to heuristic mode.", exc)
                            self._available = False
                            return None
                        logger.warning("Gemini error on %s (attempt %d): %s", model_name, attempt + 1, exc)
                        await asyncio.sleep(0.8 * (attempt + 1))

        self._available = False
        return None


gemini_client = GeminiClientWrapper()
