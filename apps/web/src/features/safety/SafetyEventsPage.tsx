import { useMemo, useState } from 'react';
import { ArrowUpRight, ShieldAlert } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { StatCard } from '../../components/ui/StatCard';
import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { Button } from '../../components/ui/Button';
import { safetyCategoryMeta, severityLabel } from './safetyCategories';
import { useSafetyDashboard } from './useSafetyDashboard';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import './safety-events.css';

const SEVERITIES = ['high', 'medium', 'low'] as const;

export function SafetyEventsPage() {
  const { events, callsById, loading, error } = useSafetyDashboard();
  const { open: openTranscript } = useTranscriptDrawer();
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);

  const countsByCategory = useMemo(() => {
    const counts = new Map<string, number>();
    for (const event of events) counts.set(event.category, (counts.get(event.category) ?? 0) + 1);
    return counts;
  }, [events]);

  const filtered = useMemo(() => {
    return events.filter((event) => {
      if (categoryFilter && event.category !== categoryFilter) return false;
      if (severityFilter && event.severity !== severityFilter) return false;
      return true;
    });
  }, [events, categoryFilter, severityFilter]);

  const hasActiveFilters = Boolean(categoryFilter || severityFilter);

  return (
    <div className="content-max safety-page">
      <Card padding="sm" className="safety-disclaimer-banner">
        <ShieldAlert size={16} aria-hidden="true" />
        <span>Operational triage support for care coordinators - not medical diagnosis.</span>
      </Card>

      {loading ? (
        <div className="safety-summary-grid"><Skeleton variant="card" count={4} /></div>
      ) : (
        <div className="safety-summary-grid">
          {Array.from(countsByCategory.entries()).map(([category, count]) => {
            const meta = safetyCategoryMeta(category);
            const Icon = meta.icon;
            const active = categoryFilter === category;
            return (
              <button
                key={category}
                type="button"
                className={`safety-stat-btn ${active ? 'active' : ''}`}
                onClick={() => setCategoryFilter(active ? null : category)}
                aria-pressed={active}
              >
                <StatCard label={meta.label} value={count} icon={<Icon size={16} />} />
              </button>
            );
          })}
        </div>
      )}

      <Card padding="sm" className="safety-filter-row">
        <span className="field-label">Severity</span>
        {SEVERITIES.map((severity) => (
          <button
            key={severity}
            type="button"
            className={`filter-chip ${severityFilter === severity ? 'active' : ''}`}
            onClick={() => setSeverityFilter(severityFilter === severity ? null : severity)}
          >
            {severityLabel(severity)}
          </button>
        ))}
        {hasActiveFilters ? (
          <Button variant="ghost" size="sm" onClick={() => { setCategoryFilter(null); setSeverityFilter(null); }}>
            Clear all
          </Button>
        ) : null}
      </Card>

      {loading ? (
        <div className="safety-event-list"><Skeleton variant="card" count={5} /></div>
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<ShieldAlert size={22} />}
          title="No safety events match"
          description="Try clearing the category or severity filters."
        />
      ) : (
        <div className="safety-event-list">
          {filtered.map((event, index) => {
            const meta = safetyCategoryMeta(event.category);
            const Icon = meta.icon;
            const call = callsById.get(event.call_id);
            return (
              <button
                key={`${event.call_id}-${event.turn_number}-${index}`}
                type="button"
                className="card card-pad-md card-interactive safety-event-card"
                onClick={() => openTranscript({ callId: event.call_id, focusTurn: event.turn_number, category: event.category })}
              >
                <div className="safety-event-top">
                  <span className="safety-event-icon" style={{ background: meta.bg, color: meta.fg }} aria-hidden="true">
                    <Icon size={16} />
                  </span>
                  <div className="safety-event-identity">
                    <strong>{meta.label}</strong>
                    <span className="safety-event-meta">
                      {call?.patient_name ?? event.call_id} · {call?.date ?? ''} · turn {event.turn_number}
                    </span>
                  </div>
                  <Badge tone={event.severity === 'high' ? 'danger' : event.severity === 'medium' ? 'warning' : 'neutral'}>
                    {severityLabel(event.severity)}
                  </Badge>
                </div>
                <p className="safety-event-quote">&ldquo;{event.matched_text}&rdquo;</p>
                <p className="safety-event-explanation">{event.explanation}</p>
                <span className="source-action">Open transcript <ArrowUpRight size={13} aria-hidden="true" /></span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
