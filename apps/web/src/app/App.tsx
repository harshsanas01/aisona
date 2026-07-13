import { useState } from 'react';
import { getCall } from '../services/api';
import type { Citation, TranscriptCall } from '../types';
import { useAskQuestion, type Filters } from '../hooks/useAskQuestion';
import {
  QuestionComposer,
  AnswerCard,
  SourceList,
  StreamingAnswerCard,
  useStreamingAnswer,
} from '../features/ask-question';
import { PatientFilterPanel } from '../features/patient-filters/PatientFilterPanel';
import { TranscriptPanel } from '../features/transcript-viewer/TranscriptPanel';
import { SafetyLegend, useSafetyEvents } from '../features/safety';

type AnswerMode = 'none' | 'sync' | 'stream';

function App() {
  const { question, setQuestion, answer, loading, error, ask } = useAskQuestion(
    'Which participants reported feeling dizzy in June?',
  );
  const streaming = useStreamingAnswer();
  const [answerMode, setAnswerMode] = useState<AnswerMode>('none');
  const [filters, setFilters] = useState<Filters>({ patientId: null, startDate: null, endDate: null });
  const [selectedTranscript, setSelectedTranscript] = useState<TranscriptCall | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [transcriptError, setTranscriptError] = useState('');
  const [activeSafetyCategory, setActiveSafetyCategory] = useState<string | null>(null);

  const safetyEvents = useSafetyEvents(selectedTranscript?.call_id ?? null);

  const resetSelection = () => {
    setSelectedTranscript(null);
    setSelectedCitation(null);
    setTranscriptError('');
  };

  const handleAsk = async (value?: string) => {
    streaming.cancel();
    resetSelection();
    setAnswerMode('sync');
    await ask(value, filters);
  };

  const handleAskStream = (value?: string) => {
    resetSelection();
    setAnswerMode('stream');
    void streaming.start(value ?? question, filters);
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
            streaming={streaming.phase === 'retrieving' || streaming.phase === 'generating'}
            onQuestionChange={setQuestion}
            onAsk={handleAsk}
            onAskStream={handleAskStream}
          />

          {error ? <div className="error">{error}</div> : null}

          {answerMode === 'sync' && answer ? (
            <>
              <AnswerCard answer={answer} />
              <SourceList citations={answer.citations} onOpenCitation={openTranscript} />
            </>
          ) : null}

          {answerMode === 'stream' ? (
            <StreamingAnswerCard
              phase={streaming.phase}
              candidateCount={streaming.candidateCount}
              answerText={streaming.answerText}
              citations={streaming.citations}
              answerable={streaming.answerable}
              error={streaming.error}
              onCancel={streaming.cancel}
              onOpenCitation={openTranscript}
            />
          ) : null}
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
