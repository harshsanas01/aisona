FROM node:20-alpine AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget -qO- http://127.0.0.1:80/ >/dev/null || exit 1
