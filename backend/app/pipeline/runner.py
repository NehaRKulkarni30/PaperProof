import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Claim, Reference, Report
from app.pipeline.claims import extract_claims_and_map
from app.pipeline.compare import compare_claim_with_source, find_best_matching_reference, tokenize
from app.pipeline.ingest import split_body_and_references
from app.pipeline.references import parse_references
from app.pipeline.retrieve import retrieve_paper
from app.sample_data import SAMPLE_PRECOMPUTED_VERDICTS

logger = logging.getLogger("paperproof.runner")


def _update_report_progress(
    db: Session,
    report_id: str,
    stage: str,
    progress: int,
    message: str,
    status: str = "processing",
    mode: Optional[str] = None,
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return
    report.stage = stage
    report.progress = progress
    report.status_message = message
    report.status = status
    if mode:
        report.mode = mode
    db.commit()


async def run_verification_pipeline(report_id: str, pages: List[Dict[str, Any]], is_sample: bool = False):
    """
    Executes the 6-stage PaperProof verification pipeline as a background task.
    Updates report progress & claims incrementally so the UI stepper streams live state.
    """
    db = SessionLocal()
    used_gemini_any = False
    try:
        _update_report_progress(
            db, report_id, stage="upload", progress=8, message="Splitting manuscript body and References section…"
        )

        # Stage 1: Split body & references
        body_pages, references_text = split_body_and_references(pages)

        # Stage 2: Reference parsing
        _update_report_progress(
            db, report_id, stage="extract", progress=18, message="Parsing bibliography entries, DOIs, and arXiv IDs…"
        )
        parsed_refs, ref_used_gemini = await parse_references(references_text)
        if ref_used_gemini:
            used_gemini_any = True

        # Persist parsed references
        db_refs: List[Reference] = []
        for r in parsed_refs:
            ref_obj = Reference(
                report_id=report_id,
                marker=r["marker"],
                raw_text=r["raw_text"],
                parsed_json=json.dumps(r["parsed"], ensure_ascii=False),
                resolved_json="{}",
                found=False,
                match_score=0.0,
            )
            db.add(ref_obj)
            db_refs.append(ref_obj)
        db.commit()
        for ref_obj in db_refs:
            db.refresh(ref_obj)

        # Stage 3: Claim extraction & citation mapping
        _update_report_progress(
            db,
            report_id,
            stage="extract",
            progress=32,
            message=f"Extracting scientific claims and mapping citations ({len(db_refs)} references parsed)…",
        )
        mapped_claims, claims_used_gemini = await extract_claims_and_map(body_pages, parsed_refs, max_claims=25)
        if claims_used_gemini:
            used_gemini_any = True

        # Persist extracted claims immediately so frontend progress stepper can stream them
        db_claims: List[Claim] = []
        for c in mapped_claims:
            ref_id = db_refs[c["reference_idx"]].id if c["reference_idx"] is not None else None
            claim_obj = Claim(
                report_id=report_id,
                idx=c["idx"],
                text=c["text"],
                page=c["page"],
                markers=json.dumps(c["markers"], ensure_ascii=False),
                reference_id=ref_id,
                verdict="processing",
                reason="Queued for source retrieval and evidence comparison…",
                confidence=0,
                confidence_note="",
                flags_json="[]",
                source_links_json="{}",
            )
            db.add(claim_obj)
            db_claims.append(claim_obj)
        db.commit()
        for claim_obj in db_claims:
            db.refresh(claim_obj)

        # Stage 4: Original paper retrieval (concurrent with semaphore)
        _update_report_progress(
            db,
            report_id,
            stage="retrieve",
            progress=45,
            message=f"Searching arXiv, CrossRef, Semantic Scholar & OpenAlex for {len(db_refs)} references…",
        )

        # Retrieve all cited references (including multi-citations like [1, 2]) plus up to 15 refs for bibliography-at-end reports
        cited_ref_indices = set()
        for c in mapped_claims:
            for r_i in c.get("reference_indices") or ([] if c["reference_idx"] is None else [c["reference_idx"]]):
                cited_ref_indices.add(r_i)
        indices_to_fetch = sorted(cited_ref_indices | set(range(min(len(db_refs), 15))))

        resolved_map: Dict[int, Dict[str, Any]] = {}
        found_map: Dict[int, bool] = {}
        progress_lock = asyncio.Lock()
        fetched_count = 0

        async def _fetch_one(idx: int):
            nonlocal fetched_count
            p_data = parsed_refs[idx]["parsed"]
            authors = p_data.get("authors") or []
            first_auth = authors[0].split(",")[0] if authors else p_data.get("title", "reference")[:35]
            yr = p_data.get("year") or ""
            via_hint = (
                "arXiv" if p_data.get("arxiv_id")
                else ("CrossRef" if p_data.get("doi")
                      else ("web source" if p_data.get("url") and not authors else "scholarly APIs"))
            )
            # retrieve_paper uses short-lived DB sessions internally — never holds a pool connection during HTTP I/O
            resolved, found, score = await retrieve_paper(p_data, db=None)
            async with progress_lock:
                fetched_count += 1
                _update_report_progress(
                    db,
                    report_id,
                    stage="retrieve",
                    progress=min(68, 46 + int(22 * fetched_count / max(len(indices_to_fetch), 1))),
                    message=f"Located {fetched_count}/{len(indices_to_fetch)}: {first_auth} {f'({yr})' if yr else ''} via {via_hint}…".strip(),
                )
            return idx, resolved, found, score

        if indices_to_fetch:
            fetch_results = await asyncio.gather(*[_fetch_one(i) for i in indices_to_fetch], return_exceptions=True)
            for item in fetch_results:
                if isinstance(item, Exception):
                    logger.warning("Reference retrieval error: %s", item)
                    continue
                idx, resolved, found, score = item
                resolved_map[idx] = resolved
                found_map[idx] = found
                # Save lighter resolved metadata (without huge chunk array) in Reference row
                light_resolved = {k: v for k, v in resolved.items() if k != "chunks"}
                light_resolved["chunk_count"] = len(resolved.get("chunks") or [])
                db_refs[idx].resolved_json = json.dumps(light_resolved, ensure_ascii=False)
                db_refs[idx].found = found
                db_refs[idx].match_score = float(score)
            db.commit()

        # Summary of other papers in the doc to help Gemini catch reference mismatches
        other_papers_summary = "; ".join(
            f"{parsed_refs[i]['marker']}: {resolved_map.get(i, {}).get('title') or parsed_refs[i]['parsed'].get('title', '')}"
            for i in range(len(parsed_refs))
        )

        # Detect student project / case study reports that list references at the end without inline [1] markers
        explicitly_cited_count = sum(1 for c in mapped_claims if not c["is_uncited"])
        is_bibliography_at_end_doc = (
            len(db_refs) > 0
            and len(mapped_claims) > 0
            and (explicitly_cited_count / len(mapped_claims)) < 0.25
        )

        def _pick_best_cited_ref(claim_text: str, ref_indices: List[int]) -> Optional[int]:
            """Among multiple cited refs (e.g. [3, 4] or [7, 8]), pick the best found reference with text chunks."""
            if not ref_indices:
                return None
            if len(ref_indices) == 1:
                return ref_indices[0]
            q_toks = set(tokenize(claim_text))
            best_i = ref_indices[0]
            best_rank = (-1, -1.0)
            for r_i in ref_indices:
                paper = resolved_map.get(r_i, {})
                found = found_map.get(r_i, False) and bool(paper.get("title"))
                chunks = paper.get("chunks") or []
                has_text = bool(chunks or paper.get("abstract"))
                tier = 2 if (found and has_text) else (1 if found else 0)
                ov = 0.0
                if has_text and q_toks:
                    all_txt = " ".join(c.get("text", "") for c in chunks[:8]) or paper.get("abstract", "")
                    c_toks = set(tokenize(all_txt))
                    ov = len(q_toks & c_toks) / max(len(q_toks), 1)
                rank = (tier, ov)
                if rank > best_rank:
                    best_rank = rank
                    best_i = r_i
            return best_i

        # Stage 5: Evidence comparison (concurrent per claim)
        _update_report_progress(
            db,
            report_id,
            stage="compare",
            progress=72,
            message=f"Comparing {len(db_claims)} claims against retrieved source passages…",
        )

        comp_sem = asyncio.Semaphore(4)
        completed_claims = 0

        async def _verify_claim(claim_idx_in_list: int):
            nonlocal completed_claims, used_gemini_any
            c_meta = mapped_claims[claim_idx_in_list]
            matched_ref_id_override: Optional[str] = None

            async with comp_sem:
                try:
                    ref_indices = c_meta.get("reference_indices") or (
                        [c_meta["reference_idx"]] if c_meta["reference_idx"] is not None else []
                    )
                    implicit_match = False

                    # For student mini-project / case study reports with references listed at the end (no inline [1]),
                    # match uncited claims against the document's own retrieved references instead of blanket 'unsupported'
                    if c_meta["is_uncited"] and is_bibliography_at_end_doc:
                        best_bib_idx = find_best_matching_reference(c_meta["text"], resolved_map, found_map)
                        if best_bib_idx is not None:
                            ref_indices = [best_bib_idx]
                            implicit_match = True
                            matched_ref_id_override = db_refs[best_bib_idx].id

                    # Case A: Uncited claim (and not matched to bibliography in a bibliography-at-end report)
                    if not ref_indices and c_meta["is_uncited"]:
                        result = {
                            "verdict": "unsupported",
                            "reason": "Uncited claim – needs a source. This factual statement contains no citation marker linking it to supporting literature.",
                            "evidence_quote": None,
                            "evidence_passage": None,
                            "evidence_location": {"section": "Body", "page": c_meta["page"]},
                            "confidence": 95,
                            "confidence_note": "No citation marker detected in this claim.",
                            "flags": ["uncited_claim"],
                            "source_links": {"found_via": "No citation provided"},
                        }
                    # Case B: Missing reference entry for cited marker
                    elif not ref_indices:
                        missing_str = ", ".join(c_meta["missing_markers"] or c_meta["markers"])
                        result = {
                            "verdict": "reference_not_found",
                            "reason": (
                                f"Citation marker {missing_str} appears in the text, but no matching entry was found "
                                f"in the document's References section."
                            ),
                            "evidence_quote": None,
                            "evidence_passage": None,
                            "evidence_location": {"section": "References", "page": c_meta["page"]},
                            "confidence": 98,
                            "confidence_note": "Missing reference entry in the document's bibliography.",
                            "flags": ["missing_reference"],
                            "source_links": {"found_via": "Missing in References section"},
                        }
                    else:
                        r_idx = _pick_best_cited_ref(c_meta["text"], ref_indices)
                        if r_idx is not None and matched_ref_id_override is None:
                            matched_ref_id_override = db_refs[r_idx].id
                        paper = resolved_map.get(r_idx, {})
                        ref_found = found_map.get(r_idx, False)

                        if not ref_found or not paper.get("title"):
                            parsed_r = parsed_refs[r_idx]["parsed"]
                            result = {
                                "verdict": "reference_not_found",
                                "reason": (
                                    f"Could not locate '{parsed_r.get('title', 'the cited paper')}' in open scholarly "
                                    f"databases (arXiv, CrossRef, Semantic Scholar, OpenAlex) or via its URL. "
                                    f"Possible non-indexed source, misspelled title, or inaccessible webpage."
                                ),
                                "evidence_quote": None,
                                "evidence_passage": None,
                                "evidence_location": {"section": "Unavailable", "page": 1},
                                "confidence": 85,
                                "confidence_note": "Title/ID match fell below verification threshold across open scholarly databases.",
                                "flags": ["missing_reference"],
                                "source_links": {"found_via": "Not found in open databases"},
                            }
                        else:
                            comp = await compare_claim_with_source(
                                claim_text=c_meta["text"],
                                paper=paper,
                                other_papers_summary=other_papers_summary,
                            )
                            if comp.get("used_gemini"):
                                used_gemini_any = True
                            elif is_sample and c_meta["idx"] in SAMPLE_PRECOMPUTED_VERDICTS:
                                # Safety-net precomputed verdicts ONLY when Gemini failed on sample document
                                pre = SAMPLE_PRECOMPUTED_VERDICTS[c_meta["idx"]]
                                comp = {
                                    **pre,
                                    "evidence_passage": comp.get("evidence_passage") or pre.get("evidence_quote"),
                                    "used_gemini": False,
                                }

                            flags = list(comp.get("flags", []))
                            conf_note = comp.get("confidence_note", "")
                            if implicit_match:
                                if "implicit_citation" not in flags:
                                    flags.append("implicit_citation")
                                ref_mk = parsed_refs[r_idx]["marker"]
                                conf_note = (
                                    f"No inline citation marker in body text; matched against {ref_mk} from the report's References section. {conf_note}"
                                ).strip()
                            elif c_meta.get("narrative_matched"):
                                ref_mk = parsed_refs[r_idx]["marker"]
                                conf_note = f"Matched via narrative author/title reference to {ref_mk}. {conf_note}".strip()

                            result = {
                                "verdict": comp["verdict"],
                                "reason": comp["reason"],
                                "evidence_quote": comp.get("evidence_quote"),
                                "evidence_passage": comp.get("evidence_passage"),
                                "evidence_location": comp.get("evidence_location", {"section": "Abstract", "page": 1}),
                                "confidence": comp.get("confidence", 70),
                                "confidence_note": conf_note,
                                "flags": sorted(set(flags)),
                                "source_links": {
                                    "found_via": paper.get("source_via", "Scholarly search"),
                                    "landing_url": paper.get("landing_url"),
                                    "pdf_url": paper.get("pdf_url"),
                                    "doi": paper.get("doi"),
                                    "arxiv_id": paper.get("arxiv_id"),
                                    "citation_count": paper.get("citation_count"),
                                    "evidence_level": paper.get("evidence_level", "abstract_only"),
                                    "is_retracted": bool(paper.get("is_retracted", False)),
                                },
                            }
                except Exception as exc:
                    logger.warning("Claim %d comparison failed: %s", c_meta["idx"], exc)
                    result = {
                        "verdict": "partly_supported",
                        "reason": "Could not verify – needs review. An automated processing error occurred while evaluating this claim.",
                        "evidence_quote": None,
                        "evidence_passage": None,
                        "evidence_location": {"section": "Unknown", "page": 1},
                        "confidence": 20,
                        "confidence_note": "Automated verification failed for this claim; please review manually.",
                        "flags": ["needs_manual_review"],
                        "source_links": {"found_via": "Verification error"},
                    }

                completed_claims += 1
                return claim_idx_in_list, result, matched_ref_id_override

        if db_claims:
            comp_results = await asyncio.gather(*[_verify_claim(i) for i in range(len(db_claims))])
            for i, res, ref_id_override in comp_results:
                c_obj = db_claims[i]
                if ref_id_override:
                    c_obj.reference_id = ref_id_override
                c_obj.verdict = res["verdict"]
                c_obj.reason = res["reason"]
                c_obj.evidence_quote = res["evidence_quote"]
                c_obj.evidence_passage = res["evidence_passage"]
                c_obj.evidence_location = json.dumps(res["evidence_location"], ensure_ascii=False)
                c_obj.confidence = int(res["confidence"])
                c_obj.confidence_note = res["confidence_note"]
                c_obj.flags_json = json.dumps(res["flags"], ensure_ascii=False)
                c_obj.source_links_json = json.dumps(res["source_links"], ensure_ascii=False)
            db.commit()

        # Stage 6: Assemble summary report
        _update_report_progress(
            db, report_id, stage="report", progress=94, message="Assembling verification report and audit summary…"
        )

        verdict_counts = {
            "supported": 0,
            "partly_supported": 0,
            "unsupported": 0,
            "reference_not_found": 0,
            "contradictory": 0,
            "possibly_outdated": 0,
        }
        mismatched_citations = 0
        missing_references = 0
        retracted_count = 0
        uncited_claims = 0

        for c_obj in db_claims:
            v = c_obj.verdict
            if v in verdict_counts:
                verdict_counts[v] += 1
            else:
                verdict_counts["unsupported"] += 1
            flags = json.loads(c_obj.flags_json or "[]")
            if "reference_mismatch" in flags:
                mismatched_citations += 1
            if "missing_reference" in flags or v == "reference_not_found":
                missing_references += 1
            if "retracted" in flags:
                retracted_count += 1
            if "uncited_claim" in flags:
                uncited_claims += 1

        total_claims = len(db_claims)
        verified_pct = round(
            100.0 * (verdict_counts["supported"] + 0.5 * verdict_counts["partly_supported"]) / max(total_claims, 1)
        )
        mode_used = "gemini" if used_gemini_any else "heuristic"

        summary = {
            "total_claims": total_claims,
            "total_references": len(db_refs),
            "verdict_counts": verdict_counts,
            "verified_pct": verified_pct,
            "misleading_references": {
                "mismatched_citations": mismatched_citations,
                "missing_references": missing_references,
                "retracted": retracted_count,
                "uncited_claims": uncited_claims,
            },
            "mode": mode_used,
        }

        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.mode = mode_used
            report.summary_json = json.dumps(summary, ensure_ascii=False)
            report.status = "completed"
            report.stage = "report"
            report.progress = 100
            report.status_message = "Verification complete. Ready for human review."
            db.commit()

    except Exception as exc:
        logger.exception("Pipeline failed for report %s", report_id)
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "failed"
            report.error_message = str(exc)
            report.status_message = f"Verification failed: {exc}"
            db.commit()
    finally:
        db.close()
