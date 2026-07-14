import type { SafetyEvent } from '../../types';
import { safetyCategoryMeta } from './safetyCategories';

interface SafetyLegendProps {
  events: SafetyEvent[];
  activeCategory: string | null;
  onCategoryChange: (category: string | null) => void;
}

export function SafetyLegend({ events, activeCategory, onCategoryChange }: SafetyLegendProps) {
  const categories = Array.from(new Set(events.map((e) => e.category)));
  if (categories.length === 0) return null;

  return (
    <div className="safety-legend">
      <p className="safety-disclaimer">
        Operational triage flags for care coordinators - not a medical diagnosis.
      </p>
      <div className="safety-chips">
        <button
          type="button"
          className={`safety-chip ${activeCategory === null ? 'active' : ''}`}
          onClick={() => onCategoryChange(null)}
        >
          All
        </button>
        {categories.map((category) => {
          const meta = safetyCategoryMeta(category);
          return (
            <button
              key={category}
              type="button"
              className={`safety-chip ${activeCategory === category ? 'active' : ''}`}
              style={{ borderColor: meta.dot }}
              onClick={() => onCategoryChange(activeCategory === category ? null : category)}
            >
              <span className="safety-dot" style={{ background: meta.dot }} />
              {meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
