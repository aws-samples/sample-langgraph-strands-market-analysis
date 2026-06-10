FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Build/runtime environment variables. Region is supplied at deploy time
# (the starter toolkit sets AWS_REGION from your deploy region; deploy.sh and
# the app resolve it from the environment / config), so it is NOT hardcoded
# here. AgentCore Memory is created and referenced at runtime, not baked in.
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1



COPY requirements.txt requirements.txt
# Install from requirements file
RUN uv pip install -r requirements.txt




RUN uv pip install aws-opentelemetry-distro==0.18.0


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

# Copy entire project (respecting .dockerignore)
COPY . .

# Use the full module path

CMD ["opentelemetry-instrument", "python", "-m", "api"]
