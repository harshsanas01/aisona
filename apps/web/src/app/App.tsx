import { useState } from 'react';
import { getCall } from '../services/api';
import type { Citation, TranscriptCall } from '../types';
import { useAskQuestion, type Filters } from '../hooks/useAskQuestion';
import { QuestionComposer, AnswerCard, SourceList } from '../features/ask-question';
import { PatientFilterPanel } from '../features/patient-filters/PatientFilterPanel';
import { TranscriptPanel } from '../features/transcript-viewer/TranscriptPanel';
import { SafetyLegend, useSafetyEvents } from '../features/safety';

function App() {
  const { question, setQuestion, answer, loading, error, ask } = useAskQuestion(
    'Which participants reported feeling dizzy in June?',
  );
  const [filters, setFilters] = useState<Filters>({ patientId: null, startDate: null, endDate: null });
  const [selectedTranscript, setSelectedTranscript] = useState<TranscriptCall | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [transcriptError, setTranscriptError] = useState('');
  const [activeSafetyCategory, setActiveSafetyCategory] = useState<string | null>(null);

  const safetyEvents = useSafetyEvents(selectedTranscript?.call_id ?? null);

  const handleAsk = async (value?: string) => {
    setSelectedTranscript(null);
    setSelectedCitation(null);
    setTranscriptError('');
    await ask(value, filters);
  };

  const openTranscript = async (citation: Citation) => {
    setSelectedCitation(citation);
    setActiveSafetyCategory(null);
    try {
      const transcript = await getCall(citation.call_id);
      setSelectedTranscript(transcript as TranscriptCall);
    } catch (err) {
      setTranscriptError(err instanceof Error ? err.message : 'Failed to open transcript');
    }
  };

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
          <PatientFilterPanel filters={filters} onChange={setFilters} />

          <QuestionComposer
            question={question}
            loading={loading}
            onQuestionChange={setQuestion}
            onAsk={handleAsk}
          />

          {error ? <div className="error">{error}</div> : null}
          {answer ? <AnswerCard answer={answer} /> : null}
          {answer ? <SourceList citations={answer.citations} onOpenCitation={openTranscript} /> : null}
        </section>

        <aside className="panel transcript-panel">
          {transcriptError ? <div className="error">{transcriptError}</div> : null}
          {selectedTranscript ? (
            <SafetyLegend
              events={safetyEvents}
              activeCategory={activeSafetyCategory}
              onCategoryChange={setActiveSafetyCategory}
            />
          ) : null}
          <TranscriptPanel
            transcript={selectedTranscript}
            activeCitation={selectedCitation}
            safetyEvents={safetyEvents}
            activeSafetyCategory={activeSafetyCategory}
            onClose={() => setSelectedTranscript(null)}
          />
        </aside>
      </main>
    </div>
  );
}

export default App;
