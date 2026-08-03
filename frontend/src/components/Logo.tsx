import Image from "next/image";

export function Logo({ size = 38, priority = false }: { size?: number; priority?: boolean }) {
  return (
    <Image
      src="/logo.svg"
      alt="Vineflow"
      width={size}
      height={size}
      priority={priority}
      className="object-contain"
      style={{ width: size, height: size }}
    />
  );
}
