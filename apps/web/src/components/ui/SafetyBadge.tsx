import { safetyCategoryMeta, severityLabel } from '../../features/safety/safetyCategories';

interface SafetyBadgeProps {
  category: string;
  severity: string;
  title?: string;
  onClick?: () => void;
}

export function SafetyBadge({ category, severity, title, onClick }: SafetyBadgeProps) {
  const meta = safetyCategoryMeta(category);
  const Icon = meta.icon;
  const content = (
    <>
      <Icon size={12} aria-hidden="true" />
      {meta.label}
      <span className={severity === 'high' ? 'safety-severity-critical' : ''}> · {severityLabel(severity)}</span>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        className="safety-badge clickable"
        style={{ background: meta.bg, color: meta.fg }}
        title={title}
        onClick={onClick}
      >
        {content}
      </button>
    );
  }

  return (
    <span className="safety-badge" style={{ background: meta.bg, color: meta.fg }} title={title}>
      {content}
    </span>
  );
}
