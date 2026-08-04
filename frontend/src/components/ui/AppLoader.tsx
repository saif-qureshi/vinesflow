"use client";

import Image from "next/image";
import type { CSSProperties } from "react";

export function AppLoaderIndicator({
  className,
  style,
}: {
  className?: string;
  style?: CSSProperties;
  percent?: number | "auto";
}) {
  return (
    <span className={`vineflow-logo-loader ${className ?? ""}`} style={style} aria-hidden="true">
      <Image
        src="/logo.png"
        alt=""
        fill
        sizes="48px"
        className="vineflow-logo-loader__grey object-contain"
      />
      <span className="vineflow-logo-loader__fill">
        <Image src="/logo.png" alt="" fill sizes="48px" className="object-contain" />
      </span>
    </span>
  );
}
