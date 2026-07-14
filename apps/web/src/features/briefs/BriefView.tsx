import { Copy, Printer, RotateCcw } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import { BRIEF_SECTION_ORDER, briefSectionLabel, briefToMarkdown } from './briefMeta';
import type { Brief, BriefBullet } from '../../types';
import './briefs.css';

interface BriefViewProps {
  brief: Brief;
  onRegenerate?: () => void;
  regenerating?: boolean;
}

export function BriefView({ brief, onRegenerate, regenerating }: BriefViewProps) {
  const { open: openTranscript } = useTranscriptDrawer();
  const toast = useToast();

  const bySection = new Map<string, BriefBullet[]>();
  for (const bullet of brief.bullets) {
    const list = bySection.get(bullet.section) ?? [];
    list.push(bullet);
    bySection.set(bullet.section, list);
  }

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(briefToMarkdown(brief));
      toast.show('Brief copied as Markdown');
    } catch {
      toast.show('Could not copy to clipboard', 'error');
    }
  };

  return (
    <div className="brief-view">
      <Card padding="md" className="brief-header no-print">
        <div className="brief-header-top">
          <div>
            <h2>{brief.brief_type === 'weekly' ? 'Weekly' : 'Daily'} Care Brief</h2>
            <span className="brief-header-meta">
              {brief.start_date} to {brief.end_date} &middot; {brief.patient_id ? brief.patient_id : 'Center-wide'}
            </span>
          </div>
          <div className="brief-header-actions">
            <Button variant="ghost" size="sm" leftIcon={<Copy size={14} />} onClick={handleCopyMarkdown}>
              Copy Markdown
            </Button>
            <Button variant="ghost" size="sm" leftIcon={<Printer size={14} />} onClick={() => window.print()}>
              Print
            </Button>
            {onRegenerate ? (
              <Button variant="secondary" size="sm" loading={regenerating} leftIcon={<RotateCcw size={14} />} onClick={onRegenerate}>
                Regenerate
              </Button>
            ) : null}
          </div>
        </div>
        <p className="brief-header-generated">
          Generated {brief.generated_at} &middot; model: {brief.model_version} &middot; prompt: {brief.prompt_version}
        </p>
      </Card>

      <div className="brief-print-header print-only">
        <h2>{brief.brief_type === 'weekly' ? 'Weekly' : 'Daily'} Care Brief</h2>
        <p>{brief.start_date} to {brief.end_date} &middot; {brief.patient_id ? brief.patient_id : 'Center-wide'}</p>
        <p>Generated {brief.generated_at} &middot; model: {brief.model_version} &middot; prompt: {brief.prompt_version}</p>
      </div>

      {brief.bullets.length === 0 ? (
        <Card padding="md">No structured events, patterns, or tasks matched this period.</Card>
      ) : (
        BRIEF_SECTION_ORDER.filter((section) => bySection.has(section)).map((section) => (
          <section key={section} className="brief-section">
            <h3>{briefSectionLabel(section)}</h3>
            <ul className="brief-bullet-list">
              {bySection.get(section)!.map((bullet) => (
                <li key={bullet.bullet_id} className="brief-bullet">
                  <strong>{bullet.patient_name}</strong>: {bullet.summary}
                  {bullet.evidence.length > 0 ? (
                    <span className="brief-bullet-evidence no-print">
                      {bullet.evidence.map((ref, index) => (
                        <button
                          key={`${ref.timeline_event_id || ref.call_id}-${index}`}
                          type="button"
                          className="source-action patient-timeline-evidence-btn"
                          onClick={() => openTranscript({
                            callId: ref.call_id, turnStart: ref.turn_start, turnEnd: ref.turn_end, focusTurn: ref.turn_start,
                          })}
                        >
                          {ref.call_id} (turn {ref.turn_start})
                        </button>
                      ))}
                    </span>
                  ) : null}
                  {bullet.related_task_id ? (
                    <Badge tone="outline" className="brief-bullet-badge">Linked task</Badge>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
