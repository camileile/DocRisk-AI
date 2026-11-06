import { batches } from "@/lib/batches";
import { BatchDetail } from "@/components/batch-detail";
export function generateStaticParams() {
  return batches.map((batch) => ({ id: batch.id }));
}
export const dynamicParams = false;
export default async function BatchPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <BatchDetail id={id} />;
}
