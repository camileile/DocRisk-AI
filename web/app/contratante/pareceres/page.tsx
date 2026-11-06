import { Suspense } from "react";
import { ContractorPortal } from "@/components/contractor-portal";
import { LoadingState } from "@/components/workspace-parts";

export default function ContractorReportsPage() {
  return <Suspense fallback={<LoadingState />}><ContractorPortal view="reports" /></Suspense>;
}
