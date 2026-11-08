# Sign-in connectivity and client error handling

Date: 8 November 2026. The user reported a timed-out login request and later confirmed that sign-in was working again before this change was deployed. The original transport failure was intermittent; these checks do not establish its underlying network cause.

Live probes reached both the same-origin frontend proxy and the direct API. Signed-out `GET /v1/auth/me` returned the expected HTTP 401; a reserved invalid-account `POST /v1/auth/login` returned HTTP 401 in 4.832 and 4.785 seconds respectively. No session was issued. A metadata-only check confirmed the administrator was active with password/MFA configured, without reading password hashes, authenticator secrets or session tokens. No account reset was needed or performed.

The frontend previously showed clinical draft/operation-key instructions for every network error, including sign-in. Authentication requests also had no client deadline. This change gives sign-in and session checks a 25-second deadline covering headers and body, retains cancellation, clears timers and supplies authentication-specific connection guidance. Sign-in failures remain unconfirmed and recommend a fresh authenticator code. No MFA submission is automatically replayed. HTTP authentication errors remain distinct from transport errors.

Eight focused Node tests passed locally, covering interrupted transport, deadline/cancellation, a stalled response body, HTTP 401, successful timer cleanup, session-check guidance, unreadable responses and no credential/OTP disclosure. They use the existing TypeScript and Node toolchain; no browser or dependency was installed. The existing Python authentication/MFA/cookie/revocation regressions remain in the full CI suite. CI now runs the focused frontend tests.

The cloud verifier now checks actual login POSTs through both origins using unique reserved invalid addresses, asserts authentication denial/no session/no-store and records response time. This supplies the POST-path coverage that signed-out GET/readiness checks alone did not provide. It creates no real accounts and sends no messages. Backend authentication, schema, keys, MFA, session rules and clinical authority are unchanged.

Exact commit, CI and deployment verification are recorded after execution.
