# ==============================================================================
# Production Dockerfile for React Vite SPA Frontend
# ==============================================================================

# --- Stage 1: Build static assets ---
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency configurations
COPY package.json package-lock.json ./

# Install project dependencies
RUN npm ci --legacy-peer-deps

# Copy full frontend codebase
COPY . .

# Run build task (runs typescript compile & vite build)
RUN npm run build

# --- Stage 2: Minimal runtime image serving via Nginx ---
FROM nginx:1.25-alpine AS runner

# Remove default static assets served by Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copy build assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy server routing configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
