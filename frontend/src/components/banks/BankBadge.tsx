"use client";

import { useState } from "react";

/** The bank's artwork, or its initials on the brand colour when it has none —
 *  including when the image fails to load. */
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
  const [failed, setFailed] = useState(false);
  const src = logoUrl && !failed ? logoUrl : null;

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
        onError={() => setFailed(true)}
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
