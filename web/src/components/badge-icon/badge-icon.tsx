import { component$ } from "@builder.io/qwik";

/**
 * One line icon per badge key (see api/app/content/letters.py). Unknown keys fall
 * back to a generic rosette so a new badge never renders empty.
 */
export const BADGE_ICON_KEYS = [
  "lantern",
  "spoke_star",
  "chain_keeper",
  "first_gear",
  "headlight",
  "tailwind",
  "kickstand",
] as const;

interface Props {
  badgeKey: string | null | undefined;
  size?: number;
  class?: string;
}

export const BadgeIcon = component$<Props>(
  ({ badgeKey, size = 40, class: cls }) => {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        stroke="currentColor"
        stroke-width="2.4"
        stroke-linecap="round"
        stroke-linejoin="round"
        class={cls}
        aria-hidden="true"
      >
        {badgeKey === "lantern" ? (
          // Lantern: a light carried forward
          <>
            <path d="M18 8h12M20 8v-3h8v3" />
            <path d="M14 12h20l-2 22H16z" />
            <path d="M24 17v9M20 23c0 3 8 3 8 0" />
            <path d="M18 34v5h12v-5" />
          </>
        ) : badgeKey === "spoke_star" ? (
          // Wheel whose spokes form a star
          <>
            <circle cx="24" cy="24" r="19" />
            <circle cx="24" cy="24" r="3.5" fill="currentColor" stroke="none" />
            <path d="M24 5v15M24 28v15M5 24h15M28 24h15M10.6 10.6l10.6 10.6M26.8 26.8l10.6 10.6M37.4 10.6 26.8 21.2M21.2 26.8 10.6 37.4" />
          </>
        ) : badgeKey === "chain_keeper" ? (
          // Three linked chain links
          <>
            <rect x="4" y="18" width="18" height="12" rx="6" />
            <rect x="26" y="18" width="18" height="12" rx="6" />
            <rect
              x="15"
              y="18"
              width="18"
              height="12"
              rx="6"
              fill="var(--card, #fff)"
            />
            <circle cx="24" cy="24" r="2" fill="currentColor" stroke="none" />
          </>
        ) : badgeKey === "first_gear" ? (
          // Cog with a "1" in the middle
          <>
            <path d="M24 4v5M24 39v5M4 24h5M39 24h5M9.9 9.9l3.5 3.5M34.6 34.6l3.5 3.5M38.1 9.9l-3.5 3.5M13.4 34.6l-3.5 3.5" />
            <circle cx="24" cy="24" r="13" />
            <path d="M21 20l3-3v14M20 31h8" />
          </>
        ) : badgeKey === "headlight" ? (
          // Lamp with light rays
          <>
            <circle cx="16" cy="24" r="9" />
            <path d="M16 19a5 5 0 0 0-5 5" />
            <path d="M30 14l9-5M30 24h12M30 34l9 5" />
          </>
        ) : badgeKey === "tailwind" ? (
          // Wind lines pushing forward
          <>
            <path d="M4 16h22a5 5 0 1 0-5-5" />
            <path d="M4 26h32a5 5 0 1 1-5 5" />
            <path d="M4 36h14a4 4 0 1 1-4 4" />
          </>
        ) : badgeKey === "kickstand" ? (
          // Bike frame resting on its kickstand
          <>
            <circle cx="11" cy="33" r="7" />
            <circle cx="37" cy="33" r="7" />
            <path d="M11 33l8-15h12l6 15M19 18l-3-5h-4M31 18l-2-6h4M19 18l5 15h-7" />
            <path d="M24 33l4 9" />
          </>
        ) : (
          // Generic rosette for unknown keys
          <>
            <circle cx="24" cy="18" r="11" />
            <path d="M17 27l-4 15 11-6 11 6-4-15" />
          </>
        )}
      </svg>
    );
  },
);
