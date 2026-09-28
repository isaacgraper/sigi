import type { Metadata } from "next";

import { Members } from "./members";

export const metadata: Metadata = { title: "Membros" };

export default function MembersPage() {
  return <Members />;
}
