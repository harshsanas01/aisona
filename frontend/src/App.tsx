import { useMemo, useState } from 'react';
import { askQuestion, getCall } from './api';
import type { AskResponse, Citation, TranscriptCall } from './types';

const sampleQuestions = [
  'What new medication did Margaret Chen start?',
  'Which participants reported feeling dizzy in June?',
  'Who has been having trouble sleeping?',
  'Has any participant fallen recently?',
  'What happened with Dorothy’s cough?',
];

function App() {
  const [question, setQuestion] = useState('Which participants reported feeling dizzy in June?');
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTranscript, setSelectedTranscript] = useState<TranscriptCall | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const handleAsk = async (value = question) => {
    setLoading(true);
    setError('');
    setAnswer(null);
    setSelectedTranscript(null);
    setSelectedCitation(null);
    try {
      const response = await askQuestion(value);
      setAnswer(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  const openTranscript = async (citation: Citation) => {
    setSelectedCitation(citation);
    try {
      const transcript = await getCall(citation.call_id);
      setSelectedTranscript(transcript as TranscriptCall);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open transcript');
    }
  };

  const answerStateLabel = useMemo(() => {
    if (!answer) return 'Awaiting input';
    return answer.answerable ? 'Answerable' : 'Not enough evidence';
  }, [answer]);

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Internal care coordination tool</p>
          <h1>CareCall Insight</h1>
          <p className="subtitle">Ask natural-language questions across care-call transcripts and inspect grounded source evidence.</p>
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <label className="field-label" htmlFor="question">Question</label>
          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={4}
            placeholder="Ask about symptoms, medications, missed rides, or other care concerns"
          />
          <div className="sample-questions">
            {sampleQuestions.map((sample) => (
              <button key={sample} type="button" onClick={() => { setQuestion(sample); void handleAsk(sample); }}>
                {sample}
              </button>
            ))}
          </div>
          <button className="primary" onClick={() => void handleAsk()} disabled={loading}>
            {loading ? 'Asking…' : 'Ask'}
          </button>

          {error ? <div className="error">{error}</div> : null}

          {answer ? (
            <div className="answer-card">
              <div className="answer-header">
                <strong>{answerStateLabel}</strong>
                <span className="pill">{answer.confidence}</span>
              </div>
              <p>{answer.answer}</p>
              <div className="debug-row">
                <span>{answer.retrieval_debug.mode}</span>
                <span>{answer.retrieval_debug.candidate_count} candidates</span>
              </div>
            </div>
          ) : null}

          {answer?.citations?.length ? (
            <div className="sources">
              <h3>Sources</h3>
              {answer.citations.map((citation, index) => (
                <button key={`${citation.call_id}-${index}`} className="source-card" onClick={() => void openTranscript(citation)}>
                  <div className="source-topline">
                    <strong>{citation.patient_name}</strong>
                    <span>{citation.date}</span>
                  </div>
                  <div className="source-meta">{citation.call_id} · turns {citation.turn_start}-{citation.turn_end}</div>
                  <p>{citation.quote}</p>
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <aside className="panel transcript-panel">
          {selectedTranscript ? (
            <>
              <div className="transcript-header">
                <div>
                  <h3>{selectedTranscript.patient.name}</h3>
                  <p>{selectedTranscript.call_id} · {selectedTranscript.date}</p>
                </div>
                <button className="secondary" onClick={() => setSelectedTranscript(null)}>Close</button>
              </div>
              <div className="turn-list">
                {selectedTranscript.turns.map((turn) => {
                  const isHighlighted = selectedCitation ? turn.turn_number >= selectedCitation.turn_start && turn.turn_number <= selectedCitation.turn_end : false;
                  return (
                    <div key={turn.turn_number} className={`turn ${isHighlighted ? 'highlighted' : ''}`}>
                      <div className="turn-badge">{turn.turn_number}</div>
                      <div>
                        <strong>{turn.speaker}</strong>
                        <p>{turn.text}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <h3>Transcript view</h3>
              <p>Select a source card to open the complete transcript and inspect the highlighted turns.</p>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

export default App;
