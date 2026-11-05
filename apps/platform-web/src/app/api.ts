export type Row = Record<string, unknown> & { id: string; name?: string; version?: number };
export interface Grant { id: string; role: string; scope_type: string; scope_id: string }
export interface Actor { id: string; name: string; email: string; grants: Grant[] }

export class ApiFailure extends Error {
  constructor(message: string, public status: number, public code: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`/v1${path}`, { ...init, credentials: "same-origin", cache: "no-store" }); }
  catch { throw new ApiFailure("The server could not be reached. Your draft is preserved. Retry with the same operation key to check the result.", 0, "NETWORK_UNAVAILABLE"); }
  if (response.status === 204) return undefined as T;
  let data;
  try { data = await response.json(); }
  catch { throw new ApiFailure("The server returned an unreadable response. The action is not confirmed.", response.status, "INVALID_RESPONSE"); }
  if (!response.ok) {
    const fields = data.error?.field_errors?.map((e: {field: string; message: string}) => `${e.field}: ${e.message}`).join("; ");
    throw new ApiFailure([data.error?.message || "The request could not be completed", fields, data.error?.correlation_id ? `Reference: ${data.error.correlation_id}` : ""].filter(Boolean).join(". "), response.status, data.error?.code || "REQUEST_FAILED");
  }
  return data as T;
}

export const text = (row: Row, key: string) => String(row[key] ?? "—");
export const human = (value: string) => value.toLowerCase().replaceAll("_", " ");
