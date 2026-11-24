/**
 * Auth calls for the public pages.
 *
 * UI only for now: each function returns a sample response after a short
 * delay. The shared types (`Role`, `User`) are exactly the ones in
 * docs/contracts.md ("Current user" and "Role check"). docs/contracts.md does
 * not yet define the sign-in, MFA or OTP endpoints, so their request and
 * response shapes below are provisional and must be confirmed with the
 * identity module owner before the TODOs are replaced with real calls.
 */

/** Roles from docs/contracts.md, "Role check". */
export const ROLES = ["borrower", "officer", "maker", "checker", "auditor", "admin"] as const;
export type Role = (typeof ROLES)[number];

/** docs/contracts.md, "Current user": User(id, org_id, role, name). Ids are uuids. */
export type User = {
  id: string;
  org_id: string;
  role: Role;
  name: string;
};

export type ApiError = {
  code: "invalid_credentials" | "invalid_code" | "expired_code" | "rate_limited";
  message: string;
};

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

// Provisional shapes (not yet in docs/contracts.md).

export type SignInRequest = { email: string; password: string };
export type SignInResponse = {
  status: "mfa_required";
  challenge_id: string;
  email: string;
};

export type VerifyMfaRequest = {
  challenge_id: string;
  method: "totp" | "recovery";
  code: string;
};
export type SessionResponse = { user: User };

export type RequestOtpRequest = { mobile: string };
export type RequestOtpResponse = {
  otp_id: string;
  /** e.g. "+91 98••• ••417" */
  masked_mobile: string;
  resend_after_seconds: number;
};

export type VerifyOtpRequest = { otp_id: string; code: string };
export type VerifyOtpResponse = { user: User; is_new: boolean };

const SAMPLE_ORG = "00000000-0000-4000-8000-00000000000a";
const LATENCY_MS = 400;

function later<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));
}

function sampleId(prefix: string): string {
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

/** Sample rule so the error state can be seen: the code 000000 is always rejected. */
const REJECTED_CODE = "000000";

/** "+91 98765 00417" -> "+91 98••• ••417" */
export function maskMobile(mobile: string): string {
  const digits = mobile.replace(/\D/g, "").slice(-10);
  return `+91 ${digits.slice(0, 2)}••• ••${digits.slice(-3)}`;
}

/**
 * Staff sign-in, first step. Always asks for the authenticator code.
 * TODO(identity): replace with POST /api/identity/sign-in.
 */
export async function signIn(req: SignInRequest): Promise<ApiResult<SignInResponse>> {
  return later({
    ok: true,
    data: { status: "mfa_required", challenge_id: sampleId("mfa"), email: req.email.trim().toLowerCase() },
  });
}

/**
 * Staff sign-in, second step (authenticator or recovery code).
 * TODO(identity): replace with POST /api/identity/mfa/verify.
 */
export async function verifyMfa(req: VerifyMfaRequest): Promise<ApiResult<SessionResponse>> {
  if (req.method === "totp" && req.code === REJECTED_CODE) {
    return later({
      ok: false,
      error: { code: "invalid_code", message: "That code did not match. Check the app and try again." },
    });
  }
  return later({
    ok: true,
    data: {
      user: {
        id: "00000000-0000-4000-8000-000000000001",
        org_id: SAMPLE_ORG,
        role: "officer",
        name: "Anita Sharma",
      },
    },
  });
}

/**
 * Borrower sign-up and sign-in, first step: send a one-time code by SMS.
 * TODO(identity): replace with POST /api/identity/otp.
 */
export async function requestOtp(req: RequestOtpRequest): Promise<ApiResult<RequestOtpResponse>> {
  return later({
    ok: true,
    data: { otp_id: sampleId("otp"), masked_mobile: maskMobile(req.mobile), resend_after_seconds: 30 },
  });
}

/**
 * Borrower sign-up and sign-in, second step: check the SMS code.
 * TODO(identity): replace with POST /api/identity/otp/verify.
 */
export async function verifyOtp(req: VerifyOtpRequest): Promise<ApiResult<VerifyOtpResponse>> {
  if (req.code === REJECTED_CODE) {
    return later({
      ok: false,
      error: { code: "invalid_code", message: "That code did not match. Check the SMS and try again." },
    });
  }
  return later({
    ok: true,
    data: {
      user: { id: "00000000-0000-4000-8000-000000000142", org_id: SAMPLE_ORG, role: "borrower", name: "Rekha K." },
      is_new: true,
    },
  });
}

/** Where each role lands after signing in. These pages arrive in later P7 tasks. */
export function homeFor(role: Role): string {
  const homes: Record<Role, string> = {
    borrower: "/borrower",
    officer: "/officer",
    maker: "/compliance",
    checker: "/checker",
    auditor: "/auditor",
    admin: "/admin",
  };
  return homes[role];
}

/** Hand-off between the sign-in and verify pages, kept for this tab only. */
export const MFA_CHALLENGE_KEY = "pratyay.mfa-challenge";
