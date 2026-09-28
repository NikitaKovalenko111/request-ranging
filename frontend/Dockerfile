FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_DATA_SOURCE=api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_DATA_SOURCE=${VITE_DATA_SOURCE}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=5s --timeout=3s --retries=20 CMD wget -qO- http://localhost/ >/dev/null || exit 1
