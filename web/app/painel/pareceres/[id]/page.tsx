import { reports } from "@/lib/reports";
import { ReportDetail } from "@/components/report-detail";
export const dynamicParams = false;
export function generateStaticParams() {
  return reports.map((report) => ({ id: report.id }));
}
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReportDetail id={id} />;
}
