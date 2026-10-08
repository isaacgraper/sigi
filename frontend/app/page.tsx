import { redirect } from "next/navigation";

import { HOME } from "@/lib/return-path";

// `/dashboard` is the single entry point (AC-0010-52).
export default function Root(): never {
  redirect(HOME);
}
