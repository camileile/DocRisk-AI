import { publishedReports } from "@/lib/published-reports";
import { PublicReportDetail } from "@/components/public-report-detail";
export const dynamicParams = false;
export function generateStaticParams() {
  return publishedReports
    .filter((p) => p.contract === "CTR-001")
    .map((p) => ({ id: p.id }));
}
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PublicReportDetail id={id} />;
}
