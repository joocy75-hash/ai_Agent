# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ========================================
# Final stage
# ========================================
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 trading && \
    mkdir -p /app/logs && \
    chown -R trading:trading /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=trading:trading . .

# Switch to non-root user
USER trading

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
# Run migrations and start application
# IMPORTANT: workers=1 필수! 여러 워커 사용 시 봇이 중복 실행됨
# 각 워커가 독립적인 메모리를 가지므로 봇 상태 공유 불가
# 성능 확장이 필요하면 Redis 기반 분산 잠금 구현 필요
CMD alembic upgrade heads || echo "Migration failed, continuing..." && uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1
