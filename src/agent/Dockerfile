# AgentCore Runtime runs Linux arm64 images. The workflows build this on an
# arm64 runner. The base image comes from ECR Public to avoid Docker Hub pull
# limits in CI.
FROM public.ecr.aws/docker/library/python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 agent
USER agent

EXPOSE 8080

# opentelemetry-instrument sends the agent's traces to AgentCore observability.
CMD ["opentelemetry-instrument", "python", "main.py"]
