# ADR-0004: OpenAPI-generated client contracts

- **Status:** Accepted
- **Date:** 2026-11-01
- **Spec refs:** §14.1, §25.2 (I0)

## Decision

- `services/api` exports `/v1/openapi.json`. `packages/api-contracts` is generated from it with `openapi-typescript`, plus a thin typed `fetch` wrapper. The wrapper attaches the bearer token, `X-Request-ID` and, for high-risk mutations, a caller-supplied `Idempotency-Key`.
- CI regenerates the types and fails on diff, so the apps and the API cannot drift silently.
- The hand-written DTOs currently in `packages/api-contracts/src/index.ts` are retired once the generated types cover the same routes.

## Consequences

- Each Pydantic request/response model in FastAPI becomes the canonical schema. Untyped `dict[str, Any]` responses are replaced by response models as each route is touched.
