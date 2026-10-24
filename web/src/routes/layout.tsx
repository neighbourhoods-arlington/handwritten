import { component$, Slot } from "@builder.io/qwik";
import { Link, useLocation } from "@builder.io/qwik-city";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/donors/", label: "Donors" },
];

export default component$(() => {
  const loc = useLocation();
  return (
    <>
      <header class="site-header">
        <nav class="nav" aria-label="Main">
          <Link href="/" class="brand">
            Phoenix Bikes <span>thank-you notes</span>
          </Link>
          <ul>
            {NAV.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  class={{ active: loc.url.pathname === item.href }}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <Slot />
    </>
  );
});
