# Vitruvius | BIM coordination software exploration

**Python backend | JavaScript frontend | IFC-related workflows | Multi-service development environment**

Vitruvius is an **early-stage construction technology repository** exploring building information modeling (BIM) coordination, model processing, issue review and related integration patterns. Its source tree includes a backend API, a web frontend, test assets, container configuration, and exploratory integration directories for Autodesk Platform Services and Revit.

**Status: prototype.** The repository is not presented as a validated production system. Features and workflows described in code or planning documents must not be interpreted as independently confirmed end-to-end capabilities.

[Backend](backend/) · [Frontend](frontend/) · [Testing documentation](TESTING.md) · [Local Docker Compose](docker-compose.yml) · [Maintainer portfolio](https://github.com/tjsasakifln/devflow/blob/main/PORTFOLIO.md)

## Engineering problem

Construction projects exchange geometry, disciplines and issues across multiple tools. Coordination requires more than viewing models: a useful system must preserve element references, identify conflicts, support engineering review and make proposed actions traceable.

This project explores that workflow from a software architecture perspective. **No claim is made here about measured cost reduction, rework reduction, clash detection accuracy or design-code compliance.**

## Repository map

| Area | Source | Intended responsibility |
| --- | --- | --- |
| Backend | [`backend/app/`](backend/app/) | HTTP API, data models, services and background tasks |
| Frontend | [`frontend/src/`](frontend/src/) | Web interface and visualization-related components |
| Development environment | [`docker-compose.yml`](docker-compose.yml) | Local backend, frontend, database, Redis and worker services |
| Tests | [`backend/tests/`](backend/tests/), [`e2e-tests/`](e2e-tests/) | Unit, integration and end-to-end test assets |
| Integrations | [`aps-integration/`](aps-integration/), [`revit-addin/`](revit-addin/) | Platform integration exploration |

Directory and test-file presence does not establish that a feature works. Inspect actual code, fixtures, dependency configuration and CI results when evaluating the implementation.

## Running and evaluating

The repository includes a [Docker Compose file](docker-compose.yml) describing a multi-service environment. Its sample database credentials and environment configuration are **development-only** and must never be treated as secure defaults for an Internet-facing deployment.

Before running it, review [`.env.example`](.env.example), local dependencies, service configuration and the [security guidance](SECURITY.md). For test intent and sample commands, see [TESTING.md](TESTING.md). That document may describe targets rather than externally verified current results.

Do not assume that starting the containers alone constitutes an end-to-end functional or security validation.

## What remains to be validated

- A reproducible complete user journey with supported sample IFC data.
- Documented interoperability scope and supported input files.
- Reproducible test execution and current coverage, rather than unverified coverage statements.
- Security assessment and configuration for any public or multi-user deployment.
- A benchmark methodology before reporting time, quality or financial improvements.

## Portfolio relevance

Vitruvius illustrates an engineering-led attempt to connect BIM domain constraints with backend, frontend and integration architecture. It is included as **exploratory work**, not as evidence of a commercially validated product.

For finished documentation, other projects and contact options, see the [maintainer's portfolio](https://github.com/tjsasakifln/devflow/blob/main/PORTFOLIO.md).

## License

Consult [LICENSE](LICENSE) before reusing code.
