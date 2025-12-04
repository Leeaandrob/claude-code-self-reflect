# Claude Self-Reflect Worker Agent
# This container monitors and manages local Claude Self-Reflect services

FROM python:3.12-slim

LABEL maintainer="Claude Self-Reflect"
LABEL description="Worker agent for monitoring and managing Claude Self-Reflect services"

# Install Docker CLI (to manage other containers)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user but allow docker group access
RUN groupadd -g 999 docker || true \
    && useradd -m -u 1000 agent \
    && usermod -aG docker agent

# Copy agent code and set ownership
COPY --chown=agent:agent agent.py .

# Health check using curl (simpler and more reliable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Expose agent API port
EXPOSE 8081

# Run as agent user
USER agent

ENTRYPOINT ["python", "agent.py"]
CMD ["--help"]
