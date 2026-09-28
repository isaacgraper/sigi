import Image from "next/image";

import { cn } from "@/lib/utils";

// Intrinsic sizes from each file's viewBox, so the space is reserved before
// the file arrives and nothing shifts.
const FILES = {
  login: { src: "/illustrations/login.svg", width: 918, height: 766 },
  "not-found": { src: "/illustrations/not-found.svg", width: 1097, height: 811 },
  error: { src: "/illustrations/error.svg", width: 663, height: 762 },
  empty: { src: "/illustrations/empty.svg", width: 820, height: 781 },
} as const;

export type IllustrationName = keyof typeof FILES;

/**
 * Decoration only (AC-0011-17): an empty text alternative, and never the only
 * carrier of a message. Static SVGs, so the optimiser has nothing to do.
 */
export function Illustration({ name, className }: { name: IllustrationName; className?: string }) {
  const file = FILES[name];
  return (
    <Image
      src={file.src}
      width={file.width}
      height={file.height}
      alt=""
      unoptimized
      data-illustration={name}
      className={cn("h-auto w-auto", className)}
    />
  );
}
