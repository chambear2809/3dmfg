# Build stage
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build argument for API URL (baked into static assets at build time)
# Empty string = relative URLs, routed through the frontend service proxy
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app

COPY --chown=node:node --from=builder /app/dist /app/dist
COPY --chown=node:node server.mjs /app/server.mjs
COPY --chown=node:node docker-entrypoint.sh /app/docker-entrypoint.sh

# sed strips Windows CRLF line endings that break the shebang on Linux
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

USER node

EXPOSE 8080
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["node", "server.mjs"]
