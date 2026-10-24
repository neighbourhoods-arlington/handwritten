# web

The frontend lives here. No framework has been chosen yet, so this is an empty
placeholder. Once you pick one:

```bash
# Example: Vite + React
cd web && npm create vite@latest . -- --template react-ts

# Example: Next.js
cd web && npx create-next-app@latest .
```

Then:

1. Keep the variables in `web/.env.example` that match your framework and copy it to `.env`.
2. Add a `Dockerfile` and uncomment the `web` service in the root `docker-compose.yml`.
3. Call the API at `http://localhost:8000/api/v1` (CORS allows `localhost:3000` and `localhost:5173`).
