// Thin fetch wrapper for the backend REST API.

export async function getAlgorithms() {
  const r = await fetch("/api/algorithms");
  if (!r.ok) throw new Error(`algorithms HTTP ${r.status}`);
  return r.json();
}

export async function postMatch(payload) {
  const r = await fetch("/api/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    const err = new Error(detail);
    err.status = r.status;
    throw err;
  }
  return r.json();
}
