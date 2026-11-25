import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MFA_CHALLENGE_KEY } from "@/lib/api/auth";
import { SignInForm } from "../sign-in/SignInForm";
import { totpSecondsLeft, VerifyForm } from "../sign-in/verify/VerifyForm";
import { SignUpForm } from "../sign-up/SignUpForm";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

beforeEach(() => {
  push.mockReset();
  sessionStorage.clear();
});
afterEach(cleanup);

describe("SignInForm", () => {
  it("shows field errors and does not submit when empty", () => {
    render(<SignInForm />);
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Enter your work email.")).toBeTruthy();
    expect(screen.getByText("Enter your password.")).toBeTruthy();
    expect(screen.getByLabelText("1 · Work email").getAttribute("aria-invalid")).toBe("true");
    expect(push).not.toHaveBeenCalled();
  });

  it("rejects short passwords", () => {
    render(<SignInForm />);
    fireEvent.change(screen.getByLabelText("1 · Work email"), { target: { value: "anita.sharma@lendera.example" } });
    fireEvent.change(screen.getByLabelText("2 · Password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText(/at least 12 characters/)).toBeTruthy();
  });

  it("signs in and opens the role's home page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      user: { id: "u1", org_id: "o1", role: "officer", name: "Anita Sharma" },
    }), { status: 200 })));
    render(<SignInForm />);
    fireEvent.change(screen.getByLabelText("1 · Work email"), { target: { value: "anita.sharma@lender-a.in" } });
    fireEvent.change(screen.getByLabelText("2 · Password"), { target: { value: "correct-horse-battery" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/officer"));
    vi.unstubAllGlobals();
  });

  it("returns to ?next= after sign-in, and shows a refusal", async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify({
      user: { id: "u1", org_id: "o1", role: "checker", name: "Rahul Mehta" },
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetch);
    render(<SignInForm next="/checker/review" />);
    fireEvent.change(screen.getByLabelText("1 · Work email"), { target: { value: "rahul.mehta@lender-a.in" } });
    fireEvent.change(screen.getByLabelText("2 · Password"), { target: { value: "correct-horse-battery" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/checker/review"));
    cleanup();
    fetch.mockImplementation(async () => new Response("{}", { status: 401 }));
    render(<SignInForm />);
    fireEvent.change(screen.getByLabelText("1 · Work email"), { target: { value: "rahul.mehta@lender-a.in" } });
    fireEvent.change(screen.getByLabelText("2 · Password"), { target: { value: "not-the-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Email or password is incorrect.")).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("with OTP off, the borrower link stays on sign-in", () => {
    render(<SignInForm />);
    const link = screen.getByRole("link", { name: /Borrower\? Sign in with your email/ });
    expect(link.getAttribute("href")).toBe("/sign-in?as=borrower");
    expect(screen.queryByText(/mobile number/)).toBeNull();
  });

  it("borrower tab asks for an email", () => {
    render(<SignInForm audience="borrower" />);
    expect(screen.getByLabelText("1 · Email")).toBeTruthy();
  });

  it("toggles password visibility", () => {
    render(<SignInForm />);
    const password = screen.getByLabelText("2 · Password");
    expect(password.getAttribute("type")).toBe("password");
    fireEvent.click(screen.getByLabelText("Show password"));
    expect(password.getAttribute("type")).toBe("text");
  });
});

describe("VerifyForm", () => {
  it("asks to start again without a challenge", () => {
    render(<VerifyForm />);
    expect(screen.getByRole("heading", { name: "Start from sign in" })).toBeTruthy();
  });

  it("verifies a 6-digit code and routes by role", async () => {
    sessionStorage.setItem(MFA_CHALLENGE_KEY, JSON.stringify({ challenge_id: "mfa-1", email: "anita@lendera.example" }));
    render(<VerifyForm />);
    expect(screen.getByText("anita@lendera.example")).toBeTruthy();
    const input = screen.getByLabelText(/6-digit code/);
    fireEvent.change(input, { target: { value: "48a1 253" } });
    expect((input as HTMLInputElement).value).toBe("481253");
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/officer"));
    expect(sessionStorage.getItem(MFA_CHALLENGE_KEY)).toBeNull();
  });

  it("shows an error for a rejected code", async () => {
    sessionStorage.setItem(MFA_CHALLENGE_KEY, JSON.stringify({ challenge_id: "mfa-1", email: "a@b.in" }));
    render(<VerifyForm />);
    fireEvent.change(screen.getByLabelText(/6-digit code/), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(push).not.toHaveBeenCalled();
  });

  it("switches to a recovery code", () => {
    sessionStorage.setItem(MFA_CHALLENGE_KEY, JSON.stringify({ challenge_id: "mfa-1", email: "a@b.in" }));
    render(<VerifyForm />);
    fireEvent.click(screen.getByRole("button", { name: "Use a recovery code" }));
    fireEvent.change(screen.getByLabelText("Recovery code"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(screen.getByText(/look like ab12-cd34/)).toBeTruthy();
  });

  it("counts down the 30-second TOTP window", () => {
    expect(totpSecondsLeft(0)).toBe(30);
    expect(totpSecondsLeft(9_000)).toBe(21);
    expect(totpSecondsLeft(29_999)).toBe(1);
  });
});

describe("SignUpForm", () => {
  it("validates the mobile number", () => {
    render(<SignUpForm />);
    fireEvent.change(screen.getByLabelText("1 · Mobile number"), { target: { value: "12345" } });
    fireEvent.click(screen.getByRole("button", { name: "Send code" }));
    expect(screen.getByText("Enter a 10-digit Indian mobile number.")).toBeTruthy();
  });

  it("sends a code, then verifies it", async () => {
    render(<SignUpForm />);
    fireEvent.change(screen.getByLabelText("1 · Mobile number"), { target: { value: "98765 00417" } });
    fireEvent.click(screen.getByRole("button", { name: "Send code" }));
    const code = await screen.findByLabelText("2 · One-time code");
    expect(screen.getByRole("button", { name: /Resend code in/ }).hasAttribute("disabled")).toBe(true);

    fireEvent.change(code, { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify and continue" }));
    expect(await screen.findByText(/did not match/)).toBeTruthy();

    fireEvent.change(code, { target: { value: "482913" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify and continue" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/borrower"));
  });

  it("asks for a new code when the number changes", async () => {
    render(<SignUpForm />);
    const mobile = screen.getByLabelText("1 · Mobile number");
    fireEvent.change(mobile, { target: { value: "9876500417" } });
    fireEvent.click(screen.getByRole("button", { name: "Send code" }));
    await screen.findByLabelText("2 · One-time code");
    await act(async () => {
      fireEvent.change(mobile, { target: { value: "9876500418" } });
    });
    expect(screen.queryByLabelText("2 · One-time code")).toBeNull();
  });
});
