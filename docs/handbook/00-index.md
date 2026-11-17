# Project handbook

This handbook describes the agent generated for **engineering-agents**. Keep it
current as the agent, its infrastructure and its workflows change.

- [Features](01-features.md): what the generated project contains.
- [Creating a component](02-creating-a-component.md): the Backstage form and what it produces.
- [Configuration](03-configuration.md): deployment parameters, tags, secrets and prerequisites.
- [Architecture](04-architecture.md): AWS resources, the request flow and the invoke interface.
- [CI/CD pipeline](05-ci-cd.md): tests, image build, deployment and branch stacks.
- [Observability](06-observability.md): logs, traces and metrics.
- [Common tasks](07-common-tasks.md): change the prompt, the model, tools and permissions.
- [The STRIDEr Slack app](08-slack-app.md): create, change and repair the Slack app.
- [STRIDEr Slack messaging](09-slack-messaging.md): how a Slack message reaches the agent and
  the reply gets back, first-time setup, and finding a failure.

## Reading in Backstage

The component's `catalog-info.yaml` contains `backstage.io/techdocs-ref: dir:.`. A central
GitHub Actions workflow builds and publishes the documentation from `docs/index.md` and the
Markdown files in `docs/handbook/`. Open the component in the catalog and select **Docs**.

This repository intentionally has no `mkdocs.yml`: the central workflow generates the MkDocs
configuration when it builds the site. The workflows in this repository do not build or publish
documentation, and pushes that change only `docs/**` or `specs/**` do not run the agent's
workflows.

## Content review

Before treating this starter handbook as the agent's operational reference, review its
instructions, IAM permissions, deployment assumptions and limits. Template-generated
documentation does not constitute human approval.
