/**
 * Calls to the FastAPI service. The browser calls /api/* on this site and Next forwards them
 * (next.config.ts), so the development role cookie goes along with every request.
 */

export class ApiFailure extends Error {
  constructor(
    public status: number,
    message: string,
    /** Rule problems from a 422, one line each. */
    public problems: string[] = [],
  ) {
    super(message);
  }
}

type Detail = string | { problems?: string[] } | { msg: string; loc?: (string | number)[] }[];

/** The message for a 401; RoleShell sends the page to sign-in when it sees it. */
export const NOT_SIGNED_IN = "You are not signed in.";

function describe(status: number, detail: Detail | undefined): ApiFailure {
  if (status === 401) return new ApiFailure(status, NOT_SIGNED_IN);
  if (typeof detail === "string") return new ApiFailure(status, detail);
  if (Array.isArray(detail)) {
    const lines = detail.map((d) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`);
    return new ApiFailure(status, "Some fields are not valid.", lines);
  }
  if (detail && Array.isArray(detail.problems)) {
    return new ApiFailure(status, "The rule does not match its paragraph yet.", detail.problems);
  }
  if (status >= 500) return new ApiFailure(status, "The service is not responding. Try again shortly.");
  return new ApiFailure(status, `Request failed (${status}).`);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      credentials: "same-origin",
      headers: body instanceof FormData || body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiFailure(0, "Cannot reach the service. Check that the API is running.");
  }
  const text = await res.text();
  let json: unknown = undefined;
  try {
    json = text ? JSON.parse(text) : undefined;
  } catch {
    // Not JSON (for example a proxy error page).
  }
  if (!res.ok) throw describe(res.status, (json as { detail?: Detail } | undefined)?.detail);
  return json as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
};

export function failureMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong.";
}
