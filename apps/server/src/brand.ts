export const LUMEN_AUTHOR = "Lumen";
export const LUMEN_REPO = "https://github.com/Lumen";
export const LUMEN_LICENSE = "Lumen Proprietary License";

export const LUMEN_SIGNATURE = Buffer.from(
  "U2lkZVJhaWwgwqkgMjAyNSBpY3ViYWJ5IOKAlCBodHRwczovL2dpdGh1Yi5jb20vaWN1YmFieS9TaWRlUmFpbCDigJQgQWxsIHJpZ2h0cyByZXNlcnZlZC4gRG8gbm90IHJlbW92ZSB0aGlzIHNpZ25hdHVyZS4=",
  "base64",
).toString("utf8");

export const LUMEN_FINGERPRINT = "sr-Lumen-2025-9f4c1a7e";

export function watermark(): Record<string, string> {
  return {
    author: LUMEN_AUTHOR,
    repo: LUMEN_REPO,
    fingerprint: LUMEN_FINGERPRINT,
  };
}
