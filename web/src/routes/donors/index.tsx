import { component$, isBrowser, useTask$ } from "@builder.io/qwik";
import {
  Form,
  Link,
  routeAction$,
  routeLoader$,
  useNavigate,
  type DocumentHead,
} from "@builder.io/qwik-city";
import { api, ApiError, type DonorListItem } from "~/lib/api";

export const useDonors = routeLoader$(async ({ env, query }) => {
  const q = query.get("q") ?? "";
  try {
    const data = await api.listDonors(env, q);
    return {
      q,
      items: data.items,
      total: data.total,
      error: null as string | null,
    };
  } catch (e) {
    return {
      q,
      items: [] as DonorListItem[],
      total: 0,
      error: (e as Error).message,
    };
  }
});

/** "Say thank-you": returns the donor's letter, drafting it with Ollama + MCP tools if needed.
 *  On success the component navigates to the letter page; refusals are shown on the row. */
export const useSayThankYou = routeAction$(async (data, { env }) => {
  const donorId = Number(data.donor_id);
  try {
    await api.sayThankYou(env, donorId);
    return {
      donorId,
      ok: true,
      message: null as string | null,
      warnings: [] as string[],
    };
  } catch (e) {
    const detail = e instanceof ApiError ? e.detail : (e as Error).message;
    return { donorId, ok: false, message: detail, warnings: [] as string[] };
  }
});

const money = (v: string | number | null) =>
  v == null
    ? "—"
    : "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });

const day = (s: string | null) =>
  s
    ? new Date(s).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "never";

export default component$(() => {
  const donors = useDonors();
  const sayThankYou = useSayThankYou();
  const { items, total, q, error } = donors.value;
  const result = sayThankYou.value;
  const nav = useNavigate();

  // Open the letter page once a draft exists (action redirects don't carry over route data)
  useTask$(({ track }) => {
    const v = track(() => sayThankYou.value);
    if (isBrowser && v?.ok) nav(`/donors/${v.donorId}/letter/`);
  });

  return (
    <main class="container">
      <h1>Donors</h1>

      <div class="bar">
        <form method="get" role="search">
          <input
            type="search"
            name="q"
            value={q}
            aria-label="Search donors"
            placeholder="Search by name, account number or email"
          />
          <button type="submit">Search</button>
        </form>
        <span class="count">
          {total} donor{total === 1 ? "" : "s"}
          {q ? ` matching “${q}”` : ""}
        </span>
      </div>

      {error && <p class="error">Could not load donors: {error}</p>}

      {items.length === 0 && !error ? (
        <div class="empty">
          {q
            ? `No donors match “${q}”.`
            : "No donors yet. Import a Bloomerang export to get started."}
        </div>
      ) : (
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Donor</th>
                <th>Account</th>
                <th class="num">Gifts</th>
                <th class="num">Given</th>
                <th>Last gift</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => {
                const rowResult =
                  result?.donorId === d.donor_id ? result : null;
                const queued = !!d.pending_note_status || rowResult?.ok;
                return (
                  <tr key={d.donor_id} class={{ rr: d.raise_ride_only }}>
                    <td>
                      <div class="name">
                        {d.first_name} {d.last_name}
                      </div>
                      <div class="muted small">
                        {d.email ?? "no email"}
                        {d.city
                          ? ` · ${d.city}${d.state ? `, ${d.state}` : ""}`
                          : ""}
                      </div>
                    </td>
                    <td class="mono">{d.account_number}</td>
                    <td class="num">
                      {d.gift_count}
                      <div class="muted small">
                        {d.direct_gift_count} direct
                      </div>
                    </td>
                    <td class="num">
                      {money(d.total_given)}
                      <div class="muted small">
                        {money(d.direct_total)} direct
                      </div>
                    </td>
                    <td class="nowrap">{day(d.last_gift_date)}</td>
                    <td>
                      {d.raise_ride_only && (
                        <span class="tag warn">Raise + Ride only</span>
                      )}
                      {!d.has_address && (
                        <span class="tag warn">No mailing address</span>
                      )}
                      {d.pending_note_status && (
                        <Link
                          href={`/donors/${d.donor_id}/letter/`}
                          class="tag info"
                        >
                          Letter #{d.pending_note_id} {d.pending_note_status}
                        </Link>
                      )}
                      {!d.raise_ride_only &&
                        d.has_address &&
                        !d.pending_note_status && (
                          <span class="tag go">Ready</span>
                        )}
                      {rowResult && (
                        <div class={rowResult.ok ? "ok" : "issue"}>
                          {rowResult.message}
                          {rowResult.warnings.map((w) => (
                            <div key={w} class="warn-text">
                              {w}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td class="actions">
                      {queued ? (
                        <Link
                          href={`/donors/${d.donor_id}/letter/`}
                          class="btn"
                        >
                          View letter
                        </Link>
                      ) : (
                        <Form action={sayThankYou}>
                          <input
                            type="hidden"
                            name="donor_id"
                            value={d.donor_id}
                          />
                          <button
                            type="submit"
                            class="primary"
                            disabled={sayThankYou.isRunning}
                            title="Draft a thank-you letter for this donor's latest direct gift"
                          >
                            {sayThankYou.isRunning &&
                            sayThankYou.formData?.get("donor_id") ===
                              String(d.donor_id)
                              ? "Drafting…"
                              : "Say thank-you"}
                          </button>
                        </Form>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
});

export const head: DocumentHead = {
  title: "Donors · Phoenix Bikes thank-you notes",
  meta: [
    {
      name: "description",
      content: "Donor list with one-click thank-you drafting",
    },
  ],
};
