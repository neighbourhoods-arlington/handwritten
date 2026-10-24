# Development image: Vite dev server with SSR and hot reload.
# For production, add a server adapter (`npm run qwik add express`) and build a
# multi-stage image that runs `node server/entry.express.js`.
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
