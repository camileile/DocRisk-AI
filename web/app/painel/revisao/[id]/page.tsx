import { reviewExamples } from "@/lib/review";
import { ReviewDetail } from "@/components/review-detail";
export const dynamicParams = false;
export function generateStaticParams() {
  return reviewExamples.map((example) => ({ id: example.documentId }));
}
export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReviewDetail id={id} />;
}
