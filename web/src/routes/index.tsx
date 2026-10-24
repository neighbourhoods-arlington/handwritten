import { component$ } from "@builder.io/qwik";
import { Link, routeLoader$, type DocumentHead } from "@builder.io/qwik-city";
import {
  api,
  type DonorListItem,
  type HealthReady,
  type OllamaStatus,
} from "~/lib/api";

interface Overview {
  health: HealthReady | null;
  ollama: OllamaStatus | null;
  donors: DonorListItem[];
  total: number;
  error: string | null;
}

export const useOverview = routeLoader$<Overview>(async ({ env }) => {
  try {
    const [health, ollama, donors] = await Promise.all([
      api.healthReady(env),
      api.ollamaStatus(env).catch(() => null),
      api.listDonors(env, "", 500),
    ]);
    return {
      health,
      ollama,
      donors: donors.items,
      total: donors.total,
      error: null,
    };
  } catch (e) {
    return {
      health: null,
      ollama: null,
      donors: [],
      total: 0,
      error: (e as Error).message,
    };
  }
});

export default component$(() => {
  const { health, ollama, donors, total, error } = useOverview().value;
  const queued = donors.filter((d) => d.pending_note_status).length;
  const rrOnly = donors.filter((d) => d.raise_ride_only).length;
  const noAddress = donors.filter((d) => !d.has_address).length;

  return (
    <main class="container">
      <h1>Overview</h1>

      {error && <p class="error">Could not reach the API: {error}</p>}

      <section>
        <h2>Backend</h2>
        <div class="figures">
          <div
            class={{ fig: true, pass: health?.status === "ok", fail: !health }}
          >
            <b>{health?.status ?? "down"}</b>
            <span>API</span>
          </div>
          <div
            class={{
              fig: true,
              pass: !!health?.database,
              fail: !health?.database,
            }}
          >
            <b>{health?.database ? "connected" : "unavailable"}</b>
            <span>PostgreSQL</span>
          </div>
          <div
            class={{ fig: true, pass: !!health?.ollama, fail: !health?.ollama }}
          >
            <b>{health?.ollama ? "connected" : "unavailable"}</b>
            <span>Ollama</span>
          </div>
        </div>
      </section>

      <section>
        <h2>Ollama</h2>
        {ollama?.available ? (
          <div class="card ollama">
            <p class="muted small">
              Ollama {ollama.version} at{" "}
              <span class="mono">{ollama.base_url}</span>
            </p>
            <div class="figures">
              <div class="fig">
                <b class="mono">{ollama.letter_model}</b>
                <span>letter model (agent + MCP tools)</span>
              </div>
              <div class="fig">
                <b class="mono">{ollama.vision_model}</b>
                <span>vision model (OCR)</span>
              </div>
            </div>
            <h3>Loaded in memory right now</h3>
            {ollama.running.length === 0 ? (
              <p class="muted small">
                Nothing loaded. Ollama loads a model on the first request and
                unloads it a few minutes after the last one.
              </p>
            ) : (
              <ul class="models">
                {ollama.running.map((m) => (
                  <li key={m.name}>
                    <span class="tag go">running</span>{" "}
                    <b class="mono">{m.name}</b>
                    <span class="muted small">
                      {" "}
                      · {m.processor} · {m.size_gb} GB
                      {m.context_length
                        ? ` · context ${m.context_length.toLocaleString()}`
                        : ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <h3>Installed</h3>
            <ul class="models">
              {ollama.installed.map((m) => (
                <li key={m.name}>
                  <b class="mono">{m.name}</b>
                  <span class="muted small">
                    {" "}
                    · {m.family ?? "?"} {m.parameters ?? ""}{" "}
                    {m.quantization ?? ""} · {m.size_gb} GB
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p class="issue">
            Ollama is not reachable{ollama?.error ? `: ${ollama.error}` : ""}.
          </p>
        )}
      </section>

      <section>
        <h2>Donors</h2>
        <div class="figures">
          <div class="fig">
            <b>{total}</b>
            <span>donors imported</span>
          </div>
          <div class="fig">
            <b>{queued}</b>
            <span>with an open thank-you note</span>
          </div>
          <div class="fig">
            <b>{rrOnly}</b>
            <span>Raise + Ride only (not thanked here)</span>
          </div>
          <div class="fig">
            <b>{noAddress}</b>
            <span>missing a mailing address</span>
          </div>
        </div>
        <Link href="/donors/" class="btn primary">
          Open the donor list
        </Link>
      </section>
    </main>
  );
});

export const head: DocumentHead = {
  title: "Overview · Phoenix Bikes thank-you notes",
  meta: [{ name: "description", content: "Backend status and donor overview" }],
};
