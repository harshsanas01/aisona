import type { ReactNode } from 'react';
import type { BadgeTone } from './Badge';

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: BadgeTone;
}

const TONE_BG: Partial<Record<BadgeTone, string>> = {
  brand: 'var(--color-brand-50)',
  success: 'var(--color-success-bg)',
  warning: 'var(--color-warning-bg)',
  danger: 'var(--color-danger-bg)',
  info: 'var(--color-info-bg)',
  violet: 'var(--color-violet-100)',
  cyan: 'var(--color-cyan-100)',
  orange: 'var(--color-orange-100)',
  rose: 'var(--color-rose-100)',
  neutral: 'var(--color-slate-100)',
};

const TONE_FG: Partial<Record<BadgeTone, string>> = {
  brand: 'var(--color-brand-700)',
  success: 'var(--color-green-700)',
  warning: 'var(--color-amber-700)',
  danger: 'var(--color-coral-700)',
  info: 'var(--color-blue-700)',
  violet: 'var(--color-violet-700)',
  cyan: 'var(--color-cyan-700)',
  orange: 'var(--color-orange-700)',
  rose: 'var(--color-rose-700)',
  neutral: 'var(--color-slate-700)',
};

export function StatCard({ label, value, icon, tone = 'brand' }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <span className="stat-card-label">{label}</span>
        {icon ? (
          <span className="stat-card-icon" style={{ background: TONE_BG[tone], color: TONE_FG[tone] }} aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </div>
      <span className="stat-card-value">{value}</span>
    </div>
  );
}
