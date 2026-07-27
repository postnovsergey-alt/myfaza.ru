FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA fallback + long cache для ассетов
RUN printf '%s\n' \
  'server {' \
  '  listen 80;' \
  '  root /usr/share/nginx/html;' \
  '  index index.html;' \
  '  location /assets/ { expires 30d; add_header Cache-Control "public, immutable"; }' \
  '  location / { try_files $uri /index.html; }' \
  '}' > /etc/nginx/conf.d/default.conf
