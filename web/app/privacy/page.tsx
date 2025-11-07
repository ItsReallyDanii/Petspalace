"use client";

import { FormEvent, useCallback, useState } from "react";

type Consent = {
  shareVectors: boolean;
  sharePhotos: boolean;
};

type CaseDetail = {
  case: {
    id: string;
    user_id: string;
    type: string;
    species: string;
    geohash6: string;
    consent: Consent;
    status: string;
    created_at: string;
  };
  photos: { id: string; view?: string | null }[];
};

type ExportPayload = {
  case: CaseDetail["case"];
  photos: CaseDetail["photos"];
  alerts: { id: string; kind: string; severity: string }[];
  events: { id: string; source: string; type: string }[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function PrivacyPage() {
  const [caseId, setCaseId] = useState<string>("");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [exportData, setExportData] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  const handleLookup = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError("");
      setMessage("");
      setExportData("");
      try {
        const resp = await fetch(`${API_BASE}/internal/cases/${caseId}`);
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        const data = (await resp.json()) as CaseDetail;
        setDetail(data);
      } catch (err: any) {
        setDetail(null);
        setError(err.message ?? "Case lookup failed");
      }
    },
    [caseId]
  );

  const handleExport = useCallback(async () => {
    if (!caseId) {
      return;
    }
    setMessage("Preparing export…");
    setError("");
    try {
      const resp = await fetch(`${API_BASE}/internal/cases/${caseId}/export`);
      if (!resp.ok) {
        throw new Error(await resp.text());
      }
      const data = (await resp.json()) as ExportPayload;
      setExportData(JSON.stringify(data, null, 2));
      setMessage("Export ready. Copy the JSON or download below.");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `case-${caseId}-export.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message ?? "Export failed");
      setMessage("");
    }
  }, [caseId]);

  const handleErase = useCallback(async () => {
    if (!caseId) {
      return;
    }
    setError("");
    setMessage("Erasing case…");
    try {
      const resp = await fetch(`${API_BASE}/internal/cases/${caseId}/erase`, {
        method: "POST",
      });
      if (!resp.ok) {
        throw new Error(await resp.text());
      }
      const data = await resp.json();
      setMessage(data.deleted ? "Case deleted successfully." : "Case not found.");
      setDetail(null);
      setExportData("");
    } catch (err: any) {
      setError(err.message ?? "Erase failed");
      setMessage("");
    }
  }, [caseId]);

  return (
    <main style={{ padding: "2rem", fontFamily: "Inter, sans-serif", maxWidth: "880px", margin: "0 auto" }}>
      <h1>Privacy Console</h1>
      <p>
        The privacy console surfaces consent flags, stored photo metadata and offers one-click
        export/erase workflows so operators can honour data-subject requests.
      </p>

      <section style={{ marginTop: "2rem" }}>
        <h2>Lookup case</h2>
        <form onSubmit={handleLookup} style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <input
            value={caseId}
            onChange={(event) => setCaseId(event.target.value)}
            placeholder="Case identifier"
            required
            style={{ flex: "1 1 auto" }}
          />
          <button type="submit">Fetch</button>
        </form>
      </section>

      {detail && (
        <section style={{ marginTop: "2rem", border: "1px solid #ddd", padding: "1rem", borderRadius: "0.5rem" }}>
          <h2>Consent &amp; metadata</h2>
          <p>
            Case <strong>{detail.case.id}</strong> created {new Date(detail.case.created_at).toLocaleString()} · status {" "}
            <strong>{detail.case.status}</strong>
          </p>
          <dl style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: "0.5rem" }}>
            <dt>User</dt>
            <dd>{detail.case.user_id}</dd>
            <dt>Species</dt>
            <dd>{detail.case.species}</dd>
            <dt>Geohash</dt>
            <dd>{detail.case.geohash6}</dd>
            <dt>Share vectors</dt>
            <dd>{detail.case.consent.shareVectors ? "Yes" : "No"}</dd>
            <dt>Share photos</dt>
            <dd>{detail.case.consent.sharePhotos ? "Yes" : "No"}</dd>
            <dt>Photo count</dt>
            <dd>{detail.photos.length}</dd>
          </dl>
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
            <button type="button" onClick={handleExport}>
              Export data
            </button>
            <button type="button" onClick={handleErase}>
              Erase case
            </button>
          </div>
        </section>
      )}

      {message && (
        <p style={{ marginTop: "1.5rem", color: "#047857" }}>
          <strong>{message}</strong>
        </p>
      )}

      {exportData && (
        <section style={{ marginTop: "1.5rem" }}>
          <h3>Export preview</h3>
          <textarea
            value={exportData}
            readOnly
            style={{ width: "100%", minHeight: "200px", fontFamily: "monospace" }}
          />
        </section>
      )}

      {error && (
        <p style={{ marginTop: "1.5rem", color: "#b91c1c" }}>
          <strong>Error:</strong> {error}
        </p>
      )}
    </main>
  );
}
