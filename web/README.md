# web

Qwik City frontend for the Handwritten project.

## Development

```bash
cp .env.example .env
npm install
npm run dev          # http://localhost:5173 (SSR dev server)
```

Or from the repo root with Docker: `docker compose up -d --build web`.

## Scripts

| Command               | What                                                         |
| --------------------- | ------------------------------------------------------------ |
| `npm run dev`         | Vite dev server with SSR                                     |
| `npm run build`       | Production build (client + types)                            |
| `npm run build.types` | Type-check only                                              |
| `npm run lint`        | ESLint                                                       |
| `npm run fmt`         | Prettier                                                     |
| `npm run qwik add`    | Add an integration (e.g. `express` server adapter, Tailwind) |

## Talking to the API

`src/lib/api.ts` wraps the backend. In `routeLoader$` / `server$` pass
`requestEvent.env` so the server-only `API_BASE_URL` is used during SSR; in the
browser `PUBLIC_API_BASE_URL` applies. See `src/routes/index.tsx` for an example.

## Production

The repo's `web/Dockerfile` runs the dev server. For a production image add a
server adapter and build it:

```bash
npm run qwik add express
npm run build
node server/entry.express.js
```
