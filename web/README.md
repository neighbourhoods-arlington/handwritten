# web

Frontend апп энд байрлана. Framework хараахан сонгогдоогүй байгаа тул
хоосон placeholder. Сонголт хийсний дараа:

```bash
# Жишээ: Vite + React
cd web && npm create vite@latest . -- --template react-ts

# Жишээ: Next.js
cd web && npx create-next-app@latest .
```

Дараа нь:

1. `web/.env.example`-д байгаа хувьсагчдаас framework-дээ тохирохыг үлдээж `.env` болгон хуулна.
2. `Dockerfile` үүсгэж, root `docker-compose.yml` доторх `web` сервисийн коммент-ийг нээнэ.
3. API-г `http://localhost:8000/api/v1` хаягаар дуудна (CORS-д `localhost:3000`, `localhost:5173` зөвшөөрөгдсөн).
