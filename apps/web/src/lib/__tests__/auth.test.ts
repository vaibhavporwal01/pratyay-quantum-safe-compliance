import { describe, expect, it } from "vitest";
import { homeFor, maskMobile, requestOtp, ROLES, signIn, verifyMfa, verifyOtp } from "../api/auth";

describe("auth sample API", () => {
  it("uses the roles from docs/contracts.md", () => {
    expect([...ROLES]).toEqual(["borrower", "officer", "maker", "checker", "auditor", "admin"]);
    for (const r of ROLES) expect(homeFor(r)).toMatch(/^\//);
  });

  it("signs staff in through an MFA challenge", async () => {
    const res = await signIn({ email: " Anita.Sharma@LenderA.example ", password: "correct-horse-battery" });
    expect(res.ok).toBe(true);
    if (!res.ok) return;
    expect(res.data.status).toBe("mfa_required");
    expect(res.data.email).toBe("anita.sharma@lendera.example");

    const ok = await verifyMfa({ challenge_id: res.data.challenge_id, method: "totp", code: "481253" });
    expect(ok.ok && ok.data.user).toMatchObject({ role: "officer", name: "Anita Sharma" });
    const user = ok.ok ? ok.data.user : null;
    expect(Object.keys(user ?? {}).sort()).toEqual(["id", "name", "org_id", "role"]);

    const bad = await verifyMfa({ challenge_id: res.data.challenge_id, method: "totp", code: "000000" });
    expect(bad).toMatchObject({ ok: false, error: { code: "invalid_code" } });
  });

  it("sends and checks a borrower OTP", async () => {
    const sent = await requestOtp({ mobile: "9876500417" });
    expect(sent.ok && sent.data.masked_mobile).toBe("+91 98••• ••417");
    if (!sent.ok) return;
    const ok = await verifyOtp({ otp_id: sent.data.otp_id, code: "482913" });
    expect(ok.ok && ok.data.user.role).toBe("borrower");
    const bad = await verifyOtp({ otp_id: sent.data.otp_id, code: "000000" });
    expect(bad.ok).toBe(false);
  });

  it("masks mobile numbers", () => {
    expect(maskMobile("+91 98765 00417")).toBe("+91 98••• ••417");
  });
});
