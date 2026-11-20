const API_BASE = "/api";

export function getToken() {
  return localStorage.getItem("paperproof_token") || sessionStorage.getItem("paperproof_token");
}

export function setToken(token, remember = true) {
  localStorage.removeItem("paperproof_token");
  sessionStorage.removeItem("paperproof_token");
  if (token) {
    if (remember) {
      localStorage.setItem("paperproof_token", token);
    } else {
      sessionStorage.setItem("paperproof_token", token);
    }
  }
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData) && !headers["Content-Type"] && options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) return null;

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    const detail =
      (data && typeof data === "object" && (data.detail || data.message)) ||
      (typeof data === "string" && data) ||
      `Request failed (${res.status})`;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    throw err;
  }

  return data;
}

export const api = {
  health: () => apiFetch("/health"),
  signup: (payload) => apiFetch("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => apiFetch("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  demoLogin: () => apiFetch("/auth/demo", { method: "POST" }),
  me: () => apiFetch("/auth/me"),
  googleAuth: (credential) =>
    apiFetch("/auth/google", { method: "POST", body: JSON.stringify({ credential }) }),

  verifyFile: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch("/verify", { method: "POST", body: fd });
  },
  verifyText: (text, filename = "Pasted_Manuscript.txt") =>
    apiFetch("/verify", { method: "POST", body: JSON.stringify({ text, filename }) }),
  runSample: () => apiFetch("/sample", { method: "POST" }),

  listReports: () => apiFetch("/reports"),
  getReport: (id) => apiFetch(`/reports/${id}`),
  getReportStatus: (id) => apiFetch(`/reports/${id}/status`),
  deleteReport: (id) => apiFetch(`/reports/${id}`, { method: "DELETE" }),
  rerunReport: (id) => apiFetch(`/reports/${id}/rerun`, { method: "POST" }),
  reviewClaim: (reportId, claimId, payload) =>
    apiFetch(`/reports/${reportId}/claims/${claimId}/review`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  toggleShare: (reportId, is_public) =>
    apiFetch(`/reports/${reportId}/share`, {
      method: "POST",
      body: JSON.stringify({ is_public }),
    }),
  getSharedReport: (token) => apiFetch(`/shared/${token}`),

  async downloadReportJson(reportId, filename) {
    const token = getToken();
    const res = await fetch(`${API_BASE}/reports/${reportId}/export.json`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to download JSON export.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `PaperProof_${(filename || "report").replace(/\.[^.]+$/, "")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
