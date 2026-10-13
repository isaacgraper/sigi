import { DashboardSkeleton } from "@/components/dashboard/dashboard-skeleton";

// The dashboard's own shape while its code arrives (SPEC-0012 AC-0012-11);
// each section then shows the same blocks as skeletons until its data does.
export default function Loading() {
  return <DashboardSkeleton />;
}
