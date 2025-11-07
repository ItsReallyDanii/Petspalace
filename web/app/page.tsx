import Link from "next/link";

const navStyle: React.CSSProperties = {
  display: "flex",
  gap: "1rem",
  marginTop: "1.5rem",
  flexWrap: "wrap",
};

export default function Home() {
  return (
    <main style={{ padding: "2rem", fontFamily: "Inter, sans-serif", lineHeight: 1.5 }}>
      <h1>Pets × AI Operations Console</h1>
      <p>
        This dashboard stitches together the three pillars of the Pets × AI platform: lost-pet
        visual search, multi-pet attribution and daycare risk analytics. Each workspace below
        talks directly to the FastAPI backend and NATS-driven event pipeline that are defined by
        the OpenAPI and AsyncAPI contracts in the repository.
      </p>
      <nav style={navStyle}>
        <Link href="/search">🐾 Lost-Pet Search</Link>
        <Link href="/alerts">🚨 Alerts</Link>
        <Link href="/privacy">🛡️ Privacy Console</Link>
      </nav>
      <section style={{ marginTop: "2rem" }}>
        <h2>Getting started</h2>
        <ol style={{ paddingLeft: "1.25rem" }}>
          <li>Create a case from the search workspace and upload a reference photo.</li>
          <li>Trigger a search to review deterministic ANN candidates with confidence bands.</li>
          <li>Run the edge consumer to ingest litter and daycare events streamed over NATS.</li>
          <li>Use the privacy console to export or erase case data with a single click.</li>
        </ol>
      </section>
    </main>
  );
}
