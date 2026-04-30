# syntax=docker/dockerfile:1

# ---------- Stage 1: build the SPA ----------
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .

# `VITE_API_BASE_URL` is baked into the bundle at build time. Override at
# build via `--build-arg` if you point the SPA at a non-default backend URL.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build


# ---------- Stage 2: serve static files via nginx ----------
FROM nginx:1.27-alpine

# Default SPA-friendly config: every unknown path falls back to index.html so
# react-router-dom routes (like /users/:nickname) work after a hard refresh.
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
