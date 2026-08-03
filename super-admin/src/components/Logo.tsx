import Image from "next/image";

export function Logo({ size = 38, priority = false }: { size?: number; priority?: boolean }) {
  return (
    <Image
      src="/logo.png"
      alt="Vineflow"
      width={size}
      height={Math.round((size * 984) / 1056)}
      priority={priority}
      className="object-contain"
      style={{ width: size, height: "auto" }}
    />
  );
}
