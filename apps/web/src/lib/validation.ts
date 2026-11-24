/** Client-side checks for the public forms. Each returns an error message or null. */

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function checkEmail(value: string): string | null {
  const v = value.trim();
  if (!v) return "Enter your work email.";
  if (!EMAIL.test(v)) return "Enter an email like name@lender.in.";
  return null;
}

export const PASSWORD_MIN = 12;

export function checkPassword(value: string): string | null {
  if (!value) return "Enter your password.";
  if (value.length < PASSWORD_MIN) return `Passwords are at least ${PASSWORD_MIN} characters.`;
  return null;
}

/** Indian mobile: 10 digits starting 6 to 9, with an optional +91 or 0 in front. */
export function normaliseMobile(value: string): string | null {
  const digits = value.replace(/[\s-]/g, "").replace(/^(\+91|91|0)(?=\d{10}$)/, "");
  return /^[6-9]\d{9}$/.test(digits) ? digits : null;
}

export function checkMobile(value: string): string | null {
  if (!value.trim()) return "Enter your mobile number.";
  if (!normaliseMobile(value)) return "Enter a 10-digit Indian mobile number.";
  return null;
}

export function checkCode(value: string, length = 6): string | null {
  if (!value) return `Enter the ${length}-digit code.`;
  if (!new RegExp(`^\\d{${length}}$`).test(value)) return `The code is ${length} digits.`;
  return null;
}

/** Recovery codes are printed as xxxx-xxxx (letters and digits). */
export function checkRecoveryCode(value: string): string | null {
  const v = value.trim();
  if (!v) return "Enter one of your recovery codes.";
  if (!/^[a-z0-9]{4}-?[a-z0-9]{4}$/i.test(v)) return "Recovery codes look like ab12-cd34.";
  return null;
}
