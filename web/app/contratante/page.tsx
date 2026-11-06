import { Suspense } from "react";
import { ContractorPortal } from "@/components/contractor-portal";
import { LoadingState } from "@/components/workspace-parts";

export default function ContractorPage() {
  return <Suspense fallback={<LoadingState />}><ContractorPortal view="overview" /></Suspense>;
}
