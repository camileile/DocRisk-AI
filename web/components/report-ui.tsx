// Safe display primitives used by the contractor portal; no internal data imports.
export function PageIntro({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="workspace-empty">
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}
