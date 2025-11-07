"use client";

import { useEffect, useMemo, useState } from "react";

type Alert = {
  id: string;
  pet_id: string;
  room_id?: string | null;
  kind: string;
  severity: string;
  state: string;
  evidence_url?: string | null;
  ts: string;
};

type EventRecord = {
  id: string;
  source: string;
  pet_id: string;
  type: string;
  ts: string;
  duration_s?: number | null;
  conf?: number | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const [alertsResp, eventsResp] = await Promise.all([
          fetch(`${API_BASE}/internal/alerts`),
          fetch(`${API_BASE}/internal/events`),
        ]);
        if (!alertsResp.ok || !eventsResp.ok) {
          throw new Error("Failed to load alert streams");
        }
        const alertsData = await alertsResp.json();
        const eventsData = await eventsResp.json();
        if (!mounted) {
          return;
        }
        setAlerts(alertsData.alerts ?? []);
        setEvents(eventsData.events ?? []);
        setError("");
      } catch (err: any) {
        if (mounted) {
          setError(err.message ?? "Unable to load alerts");
        }
      }
    }

    fetchData();
    const interval = window.setInterval(fetchData, 4000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const daycareAlerts = useMemo(
    () => alerts.filter((alert) => Boolean(alert.room_id)),
    [alerts]
  );
  const litterAlerts = useMemo(
    () => alerts.filter((alert) => !alert.room_id),
    [alerts]
  );

  return (
    <main style={{ padding: "2rem", fontFamily: "Inter, sans-serif", maxWidth: "960px", margin: "0 auto" }}>
      <h1>Alerts &amp; Anomalies</h1>
      <p>
        Live feeds from the edge consumers combine multi-pet attribution (litter/feeder telemetry)
        and daycare risk analytics. The page refreshes every few seconds to surface new events
        that have been validated against the AsyncAPI contract and persisted by the consumer.
      </p>

      <section style={{ marginTop: "2rem" }}>
        <h2>Daycare playroom alerts</h2>
        {daycareAlerts.length === 0 ? (
          <p>No playroom alerts received yet.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "0.75rem" }}>
            {daycareAlerts.map((alert) => (
              <li
                key={alert.id}
                style={{
                  border: "1px solid #ddd",
                  padding: "0.75rem",
                  borderRadius: "0.5rem",
                  background: "#fff",
                }}
              >
                <strong>{alert.kind}</strong> · room {alert.room_id} · severity {alert.severity}
                <div style={{ fontSize: "0.9rem", marginTop: "0.25rem" }}>
                  Pet {alert.pet_id} · state {alert.state} · {new Date(alert.ts).toLocaleString()}
                </div>
                {alert.evidence_url && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <a href={alert.evidence_url} target="_blank" rel="noreferrer">
                      View incident clip
                    </a>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>Multi-pet anomalies</h2>
        {litterAlerts.length === 0 ? (
          <p>No anomalies detected yet.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "0.75rem" }}>
            {litterAlerts.map((alert) => (
              <li
                key={alert.id}
                style={{ border: "1px solid #ddd", padding: "0.75rem", borderRadius: "0.5rem", background: "#fef2f2" }}
              >
                <strong>{alert.kind}</strong> for pet {alert.pet_id} (severity {alert.severity})
                <div style={{ fontSize: "0.9rem" }}>{new Date(alert.ts).toLocaleString()}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>Recent litter/feeder events</h2>
        {events.length === 0 ? (
          <p>No telemetry events recorded.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Timestamp</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Source</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Pet</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Type</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Duration (s)</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "0.5rem" }}>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td style={{ padding: "0.5rem" }}>{new Date(event.ts).toLocaleString()}</td>
                  <td style={{ padding: "0.5rem" }}>{event.source}</td>
                  <td style={{ padding: "0.5rem" }}>{event.pet_id}</td>
                  <td style={{ padding: "0.5rem" }}>{event.type}</td>
                  <td style={{ padding: "0.5rem" }}>{event.duration_s?.toFixed(1) ?? "—"}</td>
                  <td style={{ padding: "0.5rem" }}>{event.conf?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
