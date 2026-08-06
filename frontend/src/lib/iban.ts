const SHAPE = /^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$/;

/** ISO 13616: rotate the first four characters to the end, turn letters into
 *  numbers, and the result must leave a remainder of 1 mod 97. Catches the
 *  transposed digits a shape check alone lets through. */
export function ibanChecksumPasses(iban: string): boolean {
  const rotated = iban.slice(4) + iban.slice(0, 4);
  const digits = rotated.replace(/[A-Z]/g, (c) => String(c.charCodeAt(0) - 55));
  // Chunked so the value never exceeds what a JS number can hold exactly.
  let remainder = 0;
  for (const digit of digits) {
    remainder = (remainder * 10 + Number(digit)) % 97;
  }
  return remainder === 1;
}

/** Resolves when the IBAN is absent or valid, rejects with the reason when not. */
export function validateIban(value?: string): Promise<void> {
  if (!value) return Promise.resolve();
  const cleaned = value.replace(/\s/g, "").toUpperCase();
  if (!SHAPE.test(cleaned)) {
    return Promise.reject(
      new Error("An IBAN is two letters, two digits, then 11-30 letters or digits"),
    );
  }
  if (!ibanChecksumPasses(cleaned)) {
    return Promise.reject(new Error("Those check digits are wrong — look for a typo"));
  }
  return Promise.resolve();
}
