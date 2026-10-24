import { component$ } from "@builder.io/qwik";
import { routeLoader$, type DocumentHead } from "@builder.io/qwik-city";
import { api, type Document, type HealthReady } from "~/lib/api";

interface Overview {
  health: HealthReady | null;
  documents: Document[];
  error: string | null;
}

export const useOverview = routeLoader$<Overview>(async ({ env }) => {
  try {
    const [health, documents] = await Promise.all([
      api.healthReady(env),
      api.listDocuments(env, 20),
    ]);
    return { health, documents, error: null };
  } catch (e) {
    return { health: null, documents: [], error: (e as Error).message };
  }
});

export default component$(() => {
  const overview = useOverview();
  const { health, documents, error } = overview.value;

  return (
    <main class="container">
      <h1>Handwritten</h1>

      <section>
        <h2>Backend status</h2>
        {error ? (
          <p class="error">Could not reach the API: {error}</p>
        ) : (
          <ul class="status">
            <li>
              API: <strong>{health?.status}</strong>
            </li>
            <li>Database: {health?.database ? "connected" : "unavailable"}</li>
            <li>Ollama: {health?.ollama ? "connected" : "unavailable"}</li>
          </ul>
        )}
      </section>

      <section>
        <h2>Documents ({documents.length})</h2>
        {documents.length === 0 ? (
          <p class="muted">No documents yet.</p>
        ) : (
          <ul class="documents">
            {documents.map((d) => (
              <li key={d.id}>
                <strong>{d.title}</strong>
                <span class="muted">
                  {" "}
                  · {new Date(d.created_at).toLocaleString()}
                </span>
                {d.content && <p>{d.content}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
});

export const head: DocumentHead = {
  title: "Handwritten",
  meta: [
    {
      name: "description",
      content: "Handwritten — documents, MCP tools and an Ollama agent",
    },
  ],
};
