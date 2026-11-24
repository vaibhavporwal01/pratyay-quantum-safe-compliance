import { describe, expect, it } from "vitest";
import {
  checkCode,
  checkEmail,
  checkMobile,
  checkPassword,
  checkRecoveryCode,
  normaliseMobile,
} from "../validation";

describe("validation", () => {
  it("checks work emails", () => {
    expect(checkEmail("")).toMatch(/Enter your work email/);
    expect(checkEmail("anita")).toMatch(/like name@/);
    expect(checkEmail(" anita.sharma@lendera.example ")).toBeNull();
  });

  it("needs passwords of at least 12 characters", () => {
    expect(checkPassword("")).toMatch(/Enter your password/);
    expect(checkPassword("short-pass1")).toMatch(/12 characters/);
    expect(checkPassword("twelve-chars")).toBeNull();
  });

  it("accepts Indian mobile numbers in common formats", () => {
    expect(normaliseMobile("98765 00417")).toBe("9876500417");
    expect(normaliseMobile("+91 98765-00417")).toBe("9876500417");
    expect(normaliseMobile("09876500417")).toBe("9876500417");
    expect(normaliseMobile("5876500417")).toBeNull();
    expect(normaliseMobile("98765")).toBeNull();
    expect(checkMobile("")).toMatch(/Enter your mobile/);
    expect(checkMobile("12345")).toMatch(/10-digit/);
  });

  it("checks 6-digit codes", () => {
    expect(checkCode("")).toMatch(/6-digit/);
    expect(checkCode("48a2")).toMatch(/6 digits/);
    expect(checkCode("481253")).toBeNull();
  });

  it("checks recovery codes", () => {
    expect(checkRecoveryCode("ab12-cd34")).toBeNull();
    expect(checkRecoveryCode("AB12CD34")).toBeNull();
    expect(checkRecoveryCode("ab12")).toMatch(/look like/);
  });
});
