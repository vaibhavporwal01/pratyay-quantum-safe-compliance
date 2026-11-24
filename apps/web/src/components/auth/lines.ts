import type { ContextLine } from "./AuthLayout";

/** Ledger lines on the context panel, from the Dec v1 frames. */
export const SIGN_IN_LINES: ContextLine[] = [
  { label: "Sign-in", value: "time, device, organisation" },
  { label: "Each decision", value: "hash-chained and signed" },
  { label: "Idle for 15 minutes", value: "signed out" },
  { label: "Changing role", value: "needs a fresh sign-in" },
];

export const VERIFY_LINES: ContextLine[] = [
  { label: "Authenticator app", value: "TOTP, 6 digits, 30 s" },
  { label: "Lost the phone", value: "one-time recovery code" },
  { label: "Session", value: "one organisation, one role" },
  { label: "Failed codes", value: "written to the audit log" },
];
