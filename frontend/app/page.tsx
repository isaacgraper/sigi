import { redirect } from "next/navigation";

import { HOME_PATH } from "@/lib/constants";

// `/dashboard` is the single entry point (AC-0010-52).
export default function Root(): never {
  redirect(HOME_PATH);
}
