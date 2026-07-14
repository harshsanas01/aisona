import { useEffect, useState } from 'react';
import { Drawer } from '../../components/ui/Drawer';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/ErrorState';
import { getAuditQuestion } from '../../services/api';
import type { QuestionAuditRecord } from '../../types';
import './why-this-answer.css';

interface WhyThisAnswerDrawerProps {
  requestId: string | null;
  onClose: () => void;
}

export function WhyThisAnswerDrawer({ requestId, onClose }: WhyThisAnswerDrawerProps) {
  const [record, setRecord] = useState<QuestionAuditRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!requestId) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    getAuditQuestion(requestId)
      .then((result: QuestionAuditRecord | null) => { if (!cancelled) setRecord(result); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load audit record'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [requestId]);

  return (
    <Drawer open={Boolean(requestId)} onClose={onClose} labelledBy="why-this-answer-title">
      <div className="why-this-answer-content">
        <h2 id="why-this-answer-title">Why this answer?</h2>
        <p className="why-this-answer-hint">Developer/admin view - retrieval and grounding metadata, not the model's hidden reasoning.</p>

        {loading ? (
          <Skeleton variant="card" count={3} />
        ) : error ? (
          <ErrorState message={error} />
        ) : !record ? (
          <p className="field-hint">No audit record found for this answer.</p>
        ) : (
          <>
            <section className="why-section">
              <h3>Outcome</h3>
              <div className="why-badges">
                <Badge tone={record.answerable ? 'success' : 'warning'}>{record.answerable ? 'Answerable' : 'Unanswerable'}</Badge>
                <Badge tone="outline">{record.confidence} confidence</Badge>
                {record.fallback_used ? <Badge tone="danger">Fallback used</Badge> : null}
              </div>
            </section>

            <section className="why-section">
              <h3>Retrieval strategy</h3>
              <dl className="why-dl">
                <div><dt>Mode</dt><dd>{record.retrieval_mode}</dd></div>
                <div><dt>Storage mode</dt><dd>{record.storage_mode}</dd></div>
                <div><dt>Lexical / semantic weight</dt><dd>{record.lexical_weight} / {record.semantic_weight}</dd></div>
                <div><dt>Top-k</dt><dd>{record.top_k}</dd></div>
                <div><dt>Relevance threshold</dt><dd>{record.relevance_threshold}</dd></div>
              </dl>
            </section>

            <section className="why-section">
              <h3>Filters applied</h3>
              <dl className="why-dl">
                <div><dt>Patient</dt><dd>{record.filters.patient_id ?? 'None'}</dd></div>
                <div><dt>Date range</dt><dd>{record.filters.start_date ?? 'Any'} to {record.filters.end_date ?? 'Any'}</dd></div>
              </dl>
            </section>

            <section className="why-section">
              <h3>Candidates &amp; evidence</h3>
              <p className="field-hint">{record.candidate_chunk_ids.length} candidates retrieved; {record.selected_evidence_ids.length} selected as evidence.</p>
              <ul className="why-id-list">
                {record.candidate_chunk_ids.map((id) => (
                  <li key={id} className={record.selected_evidence_ids.includes(id) ? 'is-selected' : ''}>{id}</li>
                ))}
              </ul>
            </section>

            <section className="why-section">
              <h3>Model &amp; prompt</h3>
              <dl className="why-dl">
                <div><dt>Provider</dt><dd>{record.provider}</dd></div>
                <div><dt>Model</dt><dd>{record.model_name ?? 'n/a'}</dd></div>
                <div><dt>Prompt version</dt><dd>{record.prompt_version}</dd></div>
                <div><dt>Latency</dt><dd>{record.latency_ms} ms</dd></div>
              </dl>
            </section>

            <section className="why-section">
              <h3>Grounding checks</h3>
              <div className="why-badges">
                {Object.entries(record.grounding_checks).map(([check, passed]) => (
                  <Badge key={check} tone={passed ? 'success' : 'danger'}>
                    {check.replace(/_/g, ' ')}: {passed ? 'passed' : 'failed'}
                  </Badge>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </Drawer>
  );
}
