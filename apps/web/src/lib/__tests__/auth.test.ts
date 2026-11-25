import { afterEach, describe, expect, it, vi } from "vitest";
import { homeFor, maskMobile, requestOtp, ROLES, safeNext, signIn, signOut, verifyMfa, verifyOtp } from "../api/auth";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(status: number, body: unknown) {
  const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

describe("auth sample API", () => {
  it("uses the roles from docs/contracts.md", () => {
    expect([...ROLES]).toEqual(["borrower", "officer", "maker", "checker", "auditor", "admin"]);
    for (const r of ROLES) expect(homeFor(r)).toMatch(/^\//);
  });

  it("signs in against the API with JSON and returns the user", async () => {
    const user = { id: "u1", org_id: "o1", role: "officer", name: "Anita Sharma" };
    const fetch = stubFetch(200, { user });
    const res = await signIn({ email: " anita.sharma@lender-a.in ", password: "correct-horse-battery" });
    expect(res).toEqual({ ok: true, data: { user } });
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/identity/sign-in");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ email: "anita.sharma@lender-a.in", password: "correct-horse-battery" });
  });

  it("gives one message for a refused sign-in", async () => {
    stubFetch(401, { detail: "Email or password is incorrect." });
    const res = await signIn({ email: "a@b.in", password: "wrong-password-12" });
    expect(res).toMatchObject({ ok: false, error: { code: "invalid_credentials", message: "Email or password is incorrect." } });
  });

  it("signs out with a JSON POST", async () => {
    const fetch = stubFetch(204, {});
    await signOut();
    expect(fetch.mock.calls[0][0]).toBe("/api/identity/sign-out");
  });

  it("only returns to paths on this site", () => {
    expect(safeNext("/officer/applications?x=1")).toBe("/officer/applications?x=1");
    for (const bad of [null, "", "https://evil.example", "//evil.example", "/\\evil.example", "/sign-in"]) {
      expect(safeNext(bad)).toBeNull();
    }
  });

  it("keeps the authenticator sample for the identity owner", async () => {
    const res = { data: { challenge_id: "mfa-1" } };
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
