import type { Metadata } from "next";

import { Atas } from "./atas";

export const metadata: Metadata = { title: "ATAs" };

export default function AtasPage() {
  return <Atas />;
}
