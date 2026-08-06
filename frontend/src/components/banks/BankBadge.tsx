"use client";

import { useState } from "react";

/** Shows, in order of preference: the logo this org uploaded, the shared logo
 *  shipped for that bank, or its initials on the brand colour. Falls through
 *  on load failure, so a bank with no artwork yet still renders. */
export function BankBadge({
  name,
  colour,
  logoUrl,
  catalogLogo,
  size = 40,
}: {
  name: string;
  colour?: string | null;
  logoUrl?: string | null;
  catalogLogo?: string | null;
  size?: number;
}) {
  const [failed, setFailed] = useState<string | null>(null);
  const src = [logoUrl, catalogLogo].find((candidate) => candidate && candidate !== failed);

  const initials = name
    .split(/\s+/)
    .filter((word) => /^[A-Za-z]/.test(word))
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join("");

  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={name}
        width={size}
        height={size}
        onError={() => setFailed(src)}
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
