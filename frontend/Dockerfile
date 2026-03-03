# syntax=docker/dockerfile:1.6

# Stage 1: Build stage
FROM node:24-alpine AS builder

# Accept build argument for API URL
ARG VITE_API_URL
ARG VITE_ENABLE_DEV_LOGIN
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ENABLE_DEV_LOGIN=$VITE_ENABLE_DEV_LOGIN

# Create a non-root user for building
RUN addgroup -g 1001 -S frontendgroup && \
    adduser -S frontenduser -u 1001 -G frontendgroup

# Set working directory and change ownership
WORKDIR /app
RUN chown frontenduser:frontendgroup /app

# Enable Corepack for pnpm
RUN corepack enable && corepack prepare pnpm@10.27.0 --activate

# Switch to non-root user
USER frontenduser

# Note: build context is the repository root (see workflows), so paths are repo-root relative.
COPY --chown=frontenduser:frontendgroup pnpm-lock.yaml pnpm-workspace.yaml .npmrc package.json ./
COPY --chown=frontenduser:frontendgroup frontend/package.json ./frontend/package.json

# Pre-fetch dependencies into the pnpm store.
# We use a BuildKit cache mount so that even if package.json changes and the layer is re-executed,
# downloads are still reused across builds.
RUN --mount=type=cache,id=pnpm-store,target=/home/frontenduser/.local/share/pnpm/store \
    pnpm fetch --filter frontend...

# Install dependencies offline (scripts are disabled by default on pnpm v10)
RUN --mount=type=cache,id=pnpm-store,target=/home/frontenduser/.local/share/pnpm/store \
    pnpm install --offline --frozen-lockfile --filter frontend...

# Copy source code (repo-root context)
COPY --chown=frontenduser:frontendgroup frontend ./frontend

# Run build from workspace root
WORKDIR /app/frontend

# Build the application
RUN pnpm build

# Stage 2: Production stage with SocialGouv nginx4spa (rootless & read-only filesystem ready)
FROM ghcr.io/socialgouv/docker/nginx4spa:sha-9cb7d83

# Copy built application from builder stage
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
