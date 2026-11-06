import { analyses } from "@/lib/analyses";
import { AnalysisDetail } from "@/components/analysis-detail";
export const dynamicParams = false;
export function generateStaticParams() {
  return analyses.map((a) => ({ id: a.id }));
}
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AnalysisDetail id={id} />;
}
