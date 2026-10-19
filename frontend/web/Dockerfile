FROM node:24.13.0-alpine AS dependencies
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/web/package.json frontend/web/package-lock.json ./
RUN npm ci && sha256sum package-lock.json | cut -d ' ' -f 1 > node_modules/.private-iip-lock

FROM dependencies AS dev
COPY frontend/web/ ./
EXPOSE 3000
CMD ["sh", "scripts/dev-entrypoint.sh"]

FROM dependencies AS build
COPY frontend/web/ ./
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:24.13.0-alpine AS production
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
