"use client";

/** The bank's logo once one is uploaded, otherwise its initials on the brand
 *  colour — so an account is recognisable before any artwork exists. */
export function BankBadge({
  name,
  colour,
  logoUrl,
  size = 40,
}: {
  name: string;
  colour?: string | null;
  logoUrl?: string | null;
  size?: number;
}) {
  const initials = name
    .split(/\s+/)
    .filter((word) => /^[A-Za-z]/.test(word))
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join("");

  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt={name}
        width={size}
        height={size}
        className="shrink-0 rounded-lg border border-gray-100 bg-white object-contain p-1"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-lg font-semibold text-white"
      style={{
        width: size,
        height: size,
        background: colour || "#64748b",
        fontSize: size * 0.36,
      }}
    >
      {initials || "?"}
    </div>
  );
}
