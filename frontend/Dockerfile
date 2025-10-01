# Stage 1: Build stage
FROM node:24-alpine@sha256:89ec1788bd39c23adafd9f7ee14a023fcd01d08c5920745d71fb571bc7d30d1e AS builder

# Accept build argument for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Create a non-root user for building
RUN addgroup -g 1001 -S frontendgroup && \
    adduser -S frontenduser -u 1001 -G frontendgroup

# Set working directory and change ownership
WORKDIR /app
RUN chown frontenduser:frontendgroup /app

# Enable Corepack for Yarn 4 support
RUN corepack enable

# Switch to non-root user
USER frontenduser

# Copy package files (for better Docker layer caching)
COPY --chown=frontenduser:frontendgroup package.json yarn.lock .yarnrc.yml ./

# Install dependencies
RUN yarn install --immutable

# Copy source code
COPY --chown=frontenduser:frontendgroup . .

# Build the application
RUN yarn build

# Stage 2: Production stage with SocialGouv nginx4spa (rootless & read-only filesystem ready)
FROM ghcr.io/socialgouv/docker/nginx4spa:sha-9cb7d83

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
