import Image from "next/image";

import { ILLUSTRATIONS } from "@/lib/constants";
import type { IllustrationName } from "@/lib/types";
import { cn } from "@/lib/utils";


/**
 * Decoration only (AC-0011-17): an empty text alternative, and never the only
 * carrier of a message. Static SVGs, so the optimiser has nothing to do.
 */
export function Illustration({
  name,
  className,
  eager = false,
}: {
  name: IllustrationName;
  className?: string;
  /** For an illustration that is the first thing on screen, and so the LCP element. */
  eager?: boolean;
}) {
  const file = ILLUSTRATIONS[name];
  return (
    <Image
      src={file.src}
      width={file.width}
      height={file.height}
      alt=""
      unoptimized
      loading={eager ? "eager" : undefined}
      data-illustration={name}
      className={cn("h-auto w-auto", className)}
    />
  );
}
