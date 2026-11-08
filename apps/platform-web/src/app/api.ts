export type Row = Record<string, unknown> & { id: string; name?: string; version?: number };
export interface Grant { id: string; role: string; scope_type: string; scope_id: string }
export interface Actor { id: string; name: string; email: string; grants: Grant[] }

export class ApiFailure extends Error {
  constructor(message: string, public status: number, public code: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const signingIn = path === "/auth/login";
  const checkingSession = path === "/auth/me";
  const controller = signingIn || checkingSession ? new AbortController() : undefined;
  let timedOut = false;
  const abort = () => controller?.abort();
  if (init.signal?.aborted) abort();
  else init.signal?.addEventListener("abort", abort, { once: true });
  const timer = controller ? setTimeout(() => { timedOut = true; controller.abort(); }, 25_000) : undefined;
  const connectionFailure = () => new ApiFailure(
    signingIn
      ? `${timedOut ? "The sign-in service did not respond within 25 seconds." : "The connection was interrupted while signing in."} This attempt is not confirmed. Check your connection and try again with a fresh authenticator code.`
      : checkingSession
        ? "Your session could not be checked. Check your connection and reload the page."
        : "The server could not be reached. Your draft is preserved. Retry with the same operation key to check the result.",
    0, timedOut ? "REQUEST_TIMEOUT" : "NETWORK_UNAVAILABLE",
  );
  try {
    let response: Response;
    try { response = await fetch(`/v1${path}`, { ...init, ...(controller ? { signal: controller.signal } : {}), credentials: "same-origin", cache: "no-store" }); }
    catch { throw connectionFailure(); }
    if (response.status === 204) return undefined as T;
    let data;
    try { data = await response.json(); }
    catch {
      if (controller?.signal.aborted) throw connectionFailure();
      throw new ApiFailure(signingIn
        ? "The sign-in service returned an unreadable response. This attempt is not confirmed. Check your connection and try again with a fresh authenticator code."
        : "The server returned an unreadable response. The action is not confirmed.", response.status, "INVALID_RESPONSE");
    }
    if (!response.ok) {
      const fields = data.error?.field_errors?.map((e: {field: string; message: string}) => `${e.field}: ${e.message}`).join("; ");
      throw new ApiFailure([data.error?.message || "The request could not be completed", fields, data.error?.correlation_id ? `Reference: ${data.error.correlation_id}` : ""].filter(Boolean).join(". "), response.status, data.error?.code || "REQUEST_FAILED");
    }
    return data as T;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
    init.signal?.removeEventListener("abort", abort);
  }
}

export const text = (row: Row, key: string) => String(row[key] ?? "—");
export const human = (value: string) => value.toLowerCase().replaceAll("_", " ");
