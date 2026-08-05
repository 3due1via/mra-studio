import { useQuery } from "@tanstack/react-query";

type Health = { status: string; service: string; version: string };

async function loadHealth(): Promise<Health> {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${base}/health`);
  if (!response.ok) throw new Error("API non disponibile");
  return response.json() as Promise<Health>;
}

export function StatusBar() {
  const query = useQuery({
    queryKey: ["health"],
    queryFn: loadHealth,
    refetchInterval: 30_000,
  });

  return (
    <footer className="statusbar">
      <span className={query.isError ? "status-error" : "status-ready"}>
        ● {query.isError ? "API Offline" : "Ready"}
      </span>
      <span>Frontend 0.3.2</span>
      <span>API: {query.data ? `${query.data.service} ${query.data.version}` : "Verifica..."}</span>
      <span>Database: PostgreSQL</span>
    </footer>
  );
}
