"use client";

import { FormEvent, useCallback, useMemo, useState } from "react";

type Candidate = {
  pet_id: string;
  score: number;
  band: "strong" | "moderate" | "weak";
  decision?: "confirmed" | "rejected";
};

type Review = {
  id: string;
  candidate_pet_id: string;
  decision: "confirmed" | "rejected";
  band: Candidate["band"];
  score: number;
  created_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const bandColours: Record<Candidate["band"], string> = {
  strong: "#d1fae5",
  moderate: "#fef3c7",
  weak: "#f3f4f6",
};

export default function SearchPage() {
  const [caseId, setCaseId] = useState<string>("");
  const [userId, setUserId] = useState<string>("user-demo");
  const [species, setSpecies] = useState<string>("dog");
  const [geohash, setGeohash] = useState<string>("u4pruy");
  const [shareVectors, setShareVectors] = useState<boolean>(true);
  const [sharePhotos, setSharePhotos] = useState<boolean>(false);
  const [caseStatus, setCaseStatus] = useState<string>("");
  const [photoStatus, setPhotoStatus] = useState<string>("");
  const [results, setResults] = useState<Candidate[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const canSearch = useMemo(() => Boolean(caseId), [caseId]);

  const handleCreateCase = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError("");
      setCaseStatus("Creating case…");
      try {
        const resp = await fetch(`${API_BASE}/v1/cases`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            type: "lost",
            species,
            geohash6: geohash,
            consent: { shareVectors, sharePhotos },
          }),
        });
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        const data = await resp.json();
        setCaseId(data.case_id);
        setCaseStatus(`Case created with id ${data.case_id}`);
      } catch (err: any) {
        setError(err.message ?? "Failed to create case");
        setCaseStatus("Case creation failed");
      }
    },
    [geohash, sharePhotos, shareVectors, species, userId]
  );

  const handlePhotoUpload = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!caseId) {
        setError("Create a case first");
        return;
      }
      const form = event.target as HTMLFormElement;
      const fileInput = form.elements.namedItem("photo") as HTMLInputElement;
      if (!fileInput?.files?.length) {
        setError("Select a photo to upload");
        return;
      }
      setPhotoStatus("Uploading photo…");
      setError("");
      try {
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("view", "reference");
        const resp = await fetch(`${API_BASE}/v1/cases/${caseId}/photos`, {
          method: "POST",
          body: formData,
        });
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        const data = await resp.json();
        setPhotoStatus(`Photo stored with id ${data.photo_id}`);
        form.reset();
      } catch (err: any) {
        setError(err.message ?? "Failed to upload photo");
        setPhotoStatus("Upload failed");
      }
    },
    [caseId]
  );

  const fetchReviews = useCallback(
    async (currentCaseId: string) => {
      const resp = await fetch(`${API_BASE}/internal/cases/${currentCaseId}/reviews`);
      if (resp.ok) {
        const data = await resp.json();
        setReviews(data.reviews ?? []);
      }
    },
    []
  );

  const handleSearch = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!caseId) {
        setError("Create a case first");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const resp = await fetch(`${API_BASE}/v1/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ case_id: caseId, top_k: 10 }),
        });
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        const data = await resp.json();
        const enriched = (data.candidates ?? []).map((candidate: Candidate) => ({
          ...candidate,
          decision: reviews.find((r) => r.candidate_pet_id === candidate.pet_id)?.decision,
        }));
        setResults(enriched);
        fetchReviews(caseId);
      } catch (err: any) {
        setError(err.message ?? "Search failed");
      } finally {
        setLoading(false);
      }
    },
    [caseId, fetchReviews, reviews]
  );

  const handleDecision = useCallback(
    async (candidate: Candidate, decision: "confirmed" | "rejected") => {
      if (!caseId) {
        return;
      }
      try {
        const resp = await fetch(`${API_BASE}/internal/cases/${caseId}/reviews`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            candidate_pet_id: candidate.pet_id,
            band: candidate.band,
            score: candidate.score,
            decision,
          }),
        });
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        await fetchReviews(caseId);
        setResults((prev) =>
          prev.map((item) =>
            item.pet_id === candidate.pet_id ? { ...item, decision } : item
          )
        );
      } catch (err: any) {
        setError(err.message ?? "Failed to record decision");
      }
    },
    [caseId, fetchReviews]
  );

  return (
    <main style={{ padding: "2rem", fontFamily: "Inter, sans-serif", maxWidth: "960px", margin: "0 auto" }}>
      <h1>Lost-Pet Visual Search</h1>
      <p>
        Create a case, attach a reference photo and run a deterministic search against the
        mocked ANN results. Reviewers can confirm or reject candidates and the decisions are
        persisted to the database via the FastAPI backend.
      </p>

      <section style={{ marginTop: "2rem" }}>
        <h2>1. Create a case</h2>
        <form onSubmit={handleCreateCase} style={{ display: "grid", gap: "0.75rem", maxWidth: 480 }}>
          <label>
            User ID
            <input value={userId} onChange={(event) => setUserId(event.target.value)} required />
          </label>
          <label>
            Species
            <input value={species} onChange={(event) => setSpecies(event.target.value)} required />
          </label>
          <label>
            Geohash6
            <input value={geohash} onChange={(event) => setGeohash(event.target.value)} minLength={6} maxLength={12} required />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={shareVectors}
              onChange={(event) => setShareVectors(event.target.checked)}
            />
            Share vectors with other cases
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={sharePhotos}
              onChange={(event) => setSharePhotos(event.target.checked)}
            />
            Share photos with partners
          </label>
          <button type="submit">Create case</button>
        </form>
        {caseStatus && <p style={{ marginTop: "0.5rem" }}>{caseStatus}</p>}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>2. Upload a photo</h2>
        <form onSubmit={handlePhotoUpload} style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <input type="file" name="photo" accept="image/*" />
          <button type="submit" disabled={!caseId}>
            Upload
          </button>
        </form>
        {photoStatus && <p style={{ marginTop: "0.5rem" }}>{photoStatus}</p>}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>3. Review candidates</h2>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button type="submit" disabled={!canSearch || loading}>
            {loading ? "Searching…" : "Run search"}
          </button>
          {caseId && <span style={{ fontSize: "0.9rem" }}>Case: {caseId}</span>}
        </form>
        {results.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Pet ID</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Score</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Band</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Decision</th>
              </tr>
            </thead>
            <tbody>
              {results.map((candidate) => (
                <tr key={candidate.pet_id} style={{ background: bandColours[candidate.band] }}>
                  <td style={{ padding: "0.75rem 0.5rem" }}>{candidate.pet_id}</td>
                  <td style={{ padding: "0.75rem 0.5rem" }}>{candidate.score.toFixed(3)}</td>
                  <td style={{ padding: "0.75rem 0.5rem", textTransform: "capitalize" }}>{candidate.band}</td>
                  <td style={{ padding: "0.75rem 0.5rem" }}>
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      <button
                        type="button"
                        onClick={() => handleDecision(candidate, "confirmed")}
                        disabled={candidate.decision === "confirmed"}
                      >
                        Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDecision(candidate, "rejected")}
                        disabled={candidate.decision === "rejected"}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {reviews.length > 0 && (
          <aside style={{ marginTop: "1.5rem" }}>
            <h3>Review history</h3>
            <ul>
              {reviews.map((review) => (
                <li key={review.id}>
                  {review.candidate_pet_id} → {review.decision} ({review.band}, {review.score.toFixed(3)})
                </li>
              ))}
            </ul>
          </aside>
        )}
      </section>

      {error && (
        <p style={{ marginTop: "1.5rem", color: "#b91c1c" }}>
          <strong>Error:</strong> {error}
        </p>
      )}
    </main>
  );
}
