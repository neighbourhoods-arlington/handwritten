import { component$ } from "@builder.io/qwik";
import { routeLoader$, type DocumentHead } from "@builder.io/qwik-city";
import { BadgeIcon } from "~/components/badge-icon/badge-icon";
import { api, ApiError, type PublicLetter } from "~/lib/api";

/**
 * Private, token-based donor page reached from the QR code on the note.
 * Shows a badge and the thank-you, never amounts or gift details. noindex.
 */
export const usePublicLetter = routeLoader$(async ({ env, params, status }) => {
  try {
    return {
      letter: await api.publicLetter(env, params.token),
      notFound: false,
    };
  } catch (e) {
    status(e instanceof ApiError && e.status === 404 ? 404 : 502);
    return { letter: null as PublicLetter | null, notFound: true };
  }
});

export default component$(() => {
  const { letter, notFound } = usePublicLetter().value;
  if (!letter || notFound) {
    return (
      <main class="container public">
        <div class="empty">This link isn't valid anymore.</div>
      </main>
    );
  }
  return (
    <main class="container public">
      <div class="card public-card">
        {letter.badge && (
          <div class="badge">
            <BadgeIcon
              badgeKey={letter.badge.key}
              size={64}
              class="badge-icon"
            />
            <div>
              <span class="badge-title">{letter.badge.title}</span>
              <span class="small">{letter.badge.meaning}</span>
            </div>
          </div>
        )}
        <p class="letter">
          {letter.greeting ?? `Dear ${letter.first_name},`}
          <br />
          <br />
          Thank you for being part of Phoenix Bikes. {letter.impact_text}
          <br />
          <br />
          {letter.closing ?? "With gratitude, the Phoenix Bikes team"}
        </p>
        <p class="small muted">
          Follow along or give again at{" "}
          <a href={`https://${letter.donate_link}`}>{letter.donate_link}</a>
        </p>
      </div>
    </main>
  );
});

export const head: DocumentHead = {
  title: "Thank you · Phoenix Bikes",
  meta: [{ name: "robots", content: "noindex, nofollow" }],
};
