import Image from "next/image";

const LOGO_URL = "https://www.vinesflow.com/logo.png";

export function Logo({ size = 38, priority = false }: { size?: number; priority?: boolean }) {
  return (
    <Image
      src={LOGO_URL}
      alt="Vineflow"
      width={size}
      height={Math.round((size * 984) / 1056)}
      priority={priority}
      className="object-contain"
      style={{ width: size, height: "auto" }}
    />
  );
}
