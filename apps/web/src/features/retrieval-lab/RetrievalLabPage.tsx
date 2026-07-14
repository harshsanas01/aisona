import { useState } from 'react';
import { ArrowUpRight, FlaskConical } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import { compareRetrievalModes } from '../../services/api';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import type { RetrievalModeResult } from '../../types';
import './retrieval-lab.css';

const MODE_LABEL: Record<string, string> = {
  lexical: 'Lexical only',
  semantic: 'Semantic only',
  hybrid: 'Hybrid',
  hybrid_rerank: 'Hybrid + rerank',
};

export function RetrievalLabPage() {
  const [question, setQuestion] = useState('What new medication did Margaret Chen start?');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState<RetrievalModeResult[] | null>(null);
  const { open: openTranscript } = useTranscriptDrawer();

  const handleCompare = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    try {
      const compared = await compareRetrievalModes({ question });
      setResults(compared);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare retrieval modes');
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="content-max retrieval-lab-page">
      <Card padding="md">
        <Textarea
          label="Question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          hint="Runs the same question through four retrieval configurations, side by side."
          rows={3}
        />
        <Button onClick={handleCompare} loading={loading} leftIcon={<FlaskConical size={14} />}>
          Compare modes
        </Button>
        {error ? <div className="error" role="alert">{error}</div> : null}
      </Card>

      {results ? (
        <div className="retrieval-lab-grid">
          {results.map((result) => (
            <Card key={result.mode} padding="sm" className="retrieval-lab-mode-card">
              <div className="retrieval-lab-mode-header">
                <h3>{MODE_LABEL[result.mode] ?? result.mode}</h3>
                <div className="retrieval-lab-mode-badges">
                  <Badge tone="outline">lex {result.lexical_weight.toFixed(2)}</Badge>
                  <Badge tone="outline">sem {result.semantic_weight.toFixed(2)}</Badge>
                  {result.reranked ? <Badge tone="brand">reranked</Badge> : null}
                </div>
              </div>
              {result.candidates.length === 0 ? (
                <EmptyState icon={<FlaskConical size={20} />} title="No candidates" description="Nothing cleared the relevance threshold in this mode." />
              ) : (
                <ol className="retrieval-lab-candidate-list">
                  {result.candidates.map((candidate, index) => (
                    <li key={candidate.chunk_id} className="retrieval-lab-candidate">
                      <div className="retrieval-lab-candidate-top">
                        <span className="retrieval-lab-rank">#{index + 1}</span>
                        <span className="retrieval-lab-patient">{candidate.patient_name}</span>
                        <Badge tone="outline">{candidate.score.toFixed(3)}</Badge>
                      </div>
                      <p className="retrieval-lab-quote">{candidate.quote}</p>
                      <button
                        type="button"
                        className="source-action patient-timeline-evidence-btn"
                        onClick={() => openTranscript({
                          callId: candidate.call_id,
                          turnStart: candidate.turn_start,
                          turnEnd: candidate.turn_end,
                          focusTurn: candidate.turn_start,
                        })}
                      >
                        Open {candidate.call_id} (turn {candidate.turn_start}) <ArrowUpRight size={12} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}
