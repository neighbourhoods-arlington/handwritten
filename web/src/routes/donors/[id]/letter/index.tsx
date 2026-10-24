import { $, component$, useSignal } from "@builder.io/qwik";
import {
  Form,
  Link,
  routeAction$,
  routeLoader$,
  type DocumentHead,
} from "@builder.io/qwik-city";
import { BadgeIcon } from "~/components/badge-icon/badge-icon";
import { api, ApiError, type LetterResponse } from "~/lib/api";

export const useLetter = routeLoader$(async ({ env, params, status }) => {
  const donorId = Number(params.id);
  try {
    const letter = await api.getLetter(env, donorId);
    return { donorId, letter, missing: false, error: null as string | null };
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return {
        donorId,
        letter: null as LetterResponse | null,
        missing: true,
        error: null,
      };
    }
    status(502);
    return {
      donorId,
      letter: null,
      missing: false,
      error: (e as Error).message,
    };
  }
});

/** Drafts (or re-drafts a "needs attention") letter with Ollama + MCP tools. */
export const useGenerate = routeAction$(async (_data, { env, params }) => {
  try {
    const letter = await api.sayThankYou(env, Number(params.id));
    return { ok: true, letter, message: null as string | null };
  } catch (e) {
    const detail = e instanceof ApiError ? e.detail : (e as Error).message;
    return {
      ok: false,
      letter: null as LetterResponse | null,
      message: detail,
    };
  }
});

const money = (v: string) =>
  "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
const day = (s: string) =>
  new Date(s).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

export default component$(() => {
  const loaded = useLetter();
  const generate = useGenerate();
  const letter = generate.value?.letter ?? loaded.value.letter;
  const error = generate.value?.message ?? loaded.value.error;
  const toast = useSignal("");

  // Placeholder: the Uuna Tek export queue is not built yet.
  const sendToUunaTek = $(() => {
    toast.value = "Sent into the Queue: TBD";
    setTimeout(() => (toast.value = ""), 3500);
  });

  return (
    <main class="container">
      <p>
        <Link href="/donors/" class="btn back">
          Back to donors
        </Link>
      </p>

      {!letter && (
        <section class="empty">
          {error ? (
            <p class="issue">{error}</p>
          ) : (
            <p>No thank-you letter for this donor yet.</p>
          )}
          <Form action={generate}>
            <button type="submit" class="primary" disabled={generate.isRunning}>
              {generate.isRunning
                ? "Drafting with Ollama…"
                : "Draft the letter"}
            </button>
          </Form>
        </section>
      )}

      {letter && (
        <div class="letter-page">
          <div>
            <h1>
              {letter.donor.first_name} {letter.donor.last_name}
            </h1>
            <p class="muted">
              {money(letter.gift.amount)} on {day(letter.gift.gift_date)}
              {letter.gift.fund ? ` · ${letter.gift.fund}` : ""} · note #
              {letter.note.note_id} · <b>{letter.note.status}</b>
              {letter.generated ? " · just drafted" : ""}
            </p>

            {letter.needs_attention ? (
              <div class="card needs-attention">
                <p class="issue">
                  Needs attention: the model's draft was rejected after{" "}
                  {letter.note.checks?.attempts ?? 0} attempt(s).
                </p>
                <ul>
                  {letter.note.checks?.issues.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
                <Form action={generate}>
                  <button
                    type="submit"
                    class="primary"
                    disabled={generate.isRunning}
                  >
                    {generate.isRunning ? "Drafting with Ollama…" : "Try again"}
                  </button>
                </Form>
              </div>
            ) : (
              <div class="card">
                <p class="letter">{letter.note.body}</p>
                <p class="chars muted small">
                  {letter.note.body?.length ?? 0} / 520 characters
                </p>
              </div>
            )}

            {!letter.needs_attention && (
              <div class="actions-row">
                <button type="button" class="primary" onClick$={sendToUunaTek}>
                  Send to Uuna Tek
                </button>
                <span class="muted small">
                  Queues the note for the handwriting robot.
                </span>
              </div>
            )}

            {letter.warnings.length > 0 && (
              <ul class="warnings">
                {letter.warnings.map((w) => (
                  <li key={w} class="warn-text">
                    {w}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <aside class="side">
            {letter.qr_url && letter.share_url && (
              <div class="card qr">
                <img
                  src={api.publicUrl(letter.qr_url)}
                  alt="QR code to the donor's private page"
                  width="180"
                  height="180"
                />
                <p class="small">
                  Private page for {letter.donor.first_name}
                  <br />
                  <a href={letter.share_url} target="_blank" rel="noopener">
                    {letter.share_url}
                  </a>
                </p>
              </div>
            )}

            {letter.badge && (
              <div class="why badge-row">
                <BadgeIcon
                  badgeKey={letter.badge.key}
                  size={44}
                  class="badge-icon"
                />
                <div>
                  <h3>Badge: {letter.badge.title}</h3>
                  <p class="small">{letter.badge.meaning}</p>
                </div>
              </div>
            )}

            <dl>
              <dt>Impact statement</dt>
              <dd>{letter.note.impact_key ?? "—"}</dd>
              <dt>Model</dt>
              <dd>{letter.note.llm_model ?? "—"}</dd>
              <dt>MCP tools used</dt>
              <dd>{letter.note.checks?.tool_calls.join(", ") || "—"}</dd>
              <dt>Attempts</dt>
              <dd>{letter.note.checks?.attempts ?? "—"}</dd>
              {letter.gift.receipt_note && (
                <>
                  <dt>Donor wrote</dt>
                  <dd>{letter.gift.receipt_note}</dd>
                </>
              )}
              <dt>Mailing address</dt>
              <dd>
                {letter.donor.address_line ? (
                  <>
                    {letter.donor.address_line}
                    <br />
                    {letter.donor.city}, {letter.donor.state} {letter.donor.zip}
                  </>
                ) : (
                  <span class="issue">none on file</span>
                )}
              </dd>
            </dl>
            <p class="muted small">
              Approval and export happen in the review step. This page never
              marks a note approved or sent.
            </p>
          </aside>
        </div>
      )}

      <div class="toast" role="status" aria-live="polite" hidden={!toast.value}>
        {toast.value}
      </div>
    </main>
  );
});

export const head: DocumentHead = {
  title: "Thank-you letter · Phoenix Bikes",
  meta: [{ name: "robots", content: "noindex" }],
};
