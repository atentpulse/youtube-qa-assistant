# ----------------------------------------------------------------------------
# Multi-Stage Production Dockerfile for YtGenius React/Vite Frontend
# Stage 1: Build static assets using Node.js
# Stage 2: Serve static assets with hardened Alpine Nginx
# ----------------------------------------------------------------------------

# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using clean install
COPY package*.json ./
RUN npm ci --no-audit

# Copy application source code
COPY . .

# Build Vite production bundle with relative API routing for reverse proxy
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: Runner
FROM nginx:1.27-alpine AS runner

# Remove default Nginx welcome site
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/*

# Copy built production assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy optimized Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check probing local Nginx health endpoint
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:80/healthz || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
