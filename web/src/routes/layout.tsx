import { component$, Slot } from "@builder.io/qwik";
import { Link, useLocation } from "@builder.io/qwik-city";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/donors/", label: "Donors" },
];

export default component$(() => {
  const loc = useLocation();
  return (
    <>
      <header class="site-header">
        <nav class="container nav">
          <Link href="/" class="brand">
            Handwritten
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
