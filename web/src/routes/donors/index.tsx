import { component$ } from "@builder.io/qwik";
import {
  Form,
  routeAction$,
  routeLoader$,
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

/** "Say thank-you": asks the API to draft a note for the donor's latest un-thanked direct gift. */
export const useSayThankYou = routeAction$(async (data, { env }) => {
  const donorId = Number(data.donor_id);
  try {
    const res = await api.sayThankYou(env, donorId);
    return {
      donorId,
      ok: true,
      message: `Draft note #${res.note_id} created for the $${res.amount} gift on ${res.gift_date}.`,
      warnings: res.warnings,
    };
  } catch (e) {
    const detail = e instanceof ApiError ? e.detail : (e as Error).message;
    return { donorId, ok: false, message: detail, warnings: [] as string[] };
  }
});

const money = (v: string | null) =>
  v == null
    ? "—"
    : `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

export default component$(() => {
  const donors = useDonors();
  const sayThankYou = useSayThankYou();
  const { items, total, q, error } = donors.value;
  const result = sayThankYou.value;

  return (
    <main class="container">
      <h1>Donors</h1>

      <form method="get" class="search">
        <input
          type="search"
          name="q"
          value={q}
          placeholder="Search name, account number or email"
        />
        <button type="submit">Search</button>
      </form>

      {error && <p class="error">Could not load donors: {error}</p>}

      <p class="muted">
        {total} donor{total === 1 ? "" : "s"}
        {q ? ` matching "${q}"` : ""}
      </p>

      <table class="donors">
        <thead>
          <tr>
            <th>Donor</th>
            <th>Account</th>
            <th class="num">Gifts</th>
            <th class="num">Total</th>
            <th>Last gift</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((d) => {
            const rowResult = result?.donorId === d.donor_id ? result : null;
            const queued = !!d.pending_note_status || rowResult?.ok;
            return (
              <tr key={d.donor_id}>
                <td>
                  <strong>
                    {d.first_name} {d.last_name}
                  </strong>
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
                  <div class="muted small">{d.direct_gift_count} direct</div>
                </td>
                <td class="num">{money(d.total_given)}</td>
                <td>{d.last_gift_date ?? "—"}</td>
                <td>
                  {d.raise_ride_only && (
                    <span class="tag warn">Raise + Ride only</span>
                  )}
                  {!d.has_address && (
                    <span class="tag warn">No mailing address</span>
                  )}
                  {d.pending_note_status && (
                    <span class="tag info">
                      Note #{d.pending_note_id} {d.pending_note_status}
                    </span>
                  )}
                  {rowResult && (
                    <div
                      class={{
                        small: true,
                        ok: rowResult.ok,
                        error: !rowResult.ok,
                      }}
                    >
                      {rowResult.message}
                      {rowResult.warnings.map((w) => (
                        <div key={w} class="warn-text">
                          {w}
                        </div>
                      ))}
                    </div>
                  )}
                </td>
                <td>
                  <Form action={sayThankYou}>
                    <input type="hidden" name="donor_id" value={d.donor_id} />
                    <button
                      type="submit"
                      class="primary"
                      disabled={sayThankYou.isRunning || queued}
                      title={
                        queued
                          ? "This donor already has an open thank-you note"
                          : "Draft a thank-you note for this donor's latest direct gift"
                      }
                    >
                      Say thank-you
                    </button>
                  </Form>
                </td>
              </tr>
            );
          })}
          {items.length === 0 && !error && (
            <tr>
              <td colSpan={7} class="muted">
                No donors yet. Import a Bloomerang export to get started.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  );
});

export const head: DocumentHead = {
  title: "Donors · Handwritten",
  meta: [
    {
      name: "description",
      content: "Donor list with one-click thank-you drafting",
    },
  ],
};
