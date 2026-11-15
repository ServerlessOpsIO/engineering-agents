# AgentCore Runtime runs Linux arm64 images. The workflows build this on an
# arm64 runner. The base image comes from ECR Public to avoid Docker Hub pull
# limits in CI.
FROM public.ecr.aws/docker/library/python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# The build context is the repository root, where the Pipfile lives. Only the
# runtime packages in Pipfile.lock are installed, into the system Python.
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv \
    && pipenv install --system --deploy \
    && pip uninstall --yes pipenv \
    && rm -rf /root/.cache Pipfile Pipfile.lock

COPY src/agent/ .

RUN useradd --create-home --uid 1000 agent
USER agent

EXPOSE 8080

# opentelemetry-instrument sends the agent's traces to AgentCore observability.
CMD ["opentelemetry-instrument", "python", "main.py"]
