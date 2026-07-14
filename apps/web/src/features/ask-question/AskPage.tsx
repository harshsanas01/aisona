import { useState } from 'react';
import { Card } from '../../components/ui/Card';
import { useAskQuestion, type Filters } from '../../hooks/useAskQuestion';
import { useHealth } from '../../hooks/useHealth';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import { PatientFilterPanel } from '../patient-filters/PatientFilterPanel';
import { QuestionComposer } from './QuestionComposer';
import { AnswerCard } from './AnswerCard';
import { SourceList } from './SourceList';
import { StreamingAnswerCard } from './StreamingAnswerCard';
import { useStreamingAnswer } from './useStreamingAnswer';
import { WhyThisAnswerDrawer } from './WhyThisAnswerDrawer';
import type { Citation } from '../../types';
import './ask-page.css';

type AnswerMode = 'none' | 'sync' | 'stream';

export function AskPage() {
  const { question, setQuestion, answer, loading, error, ask } = useAskQuestion(
    'Which participants reported feeling dizzy in June?',
  );
  const streaming = useStreamingAnswer();
  const { health } = useHealth();
  const [answerMode, setAnswerMode] = useState<AnswerMode>('none');
  const [filters, setFilters] = useState<Filters>({ patientId: null, startDate: null, endDate: null });
  const [whyRequestId, setWhyRequestId] = useState<string | null>(null);
  const { open: openTranscript } = useTranscriptDrawer();

  const handleAsk = async (value?: string) => {
    streaming.cancel();
    setAnswerMode('sync');
    await ask(value, filters);
  };

  const handleAskStream = (value?: string) => {
    setAnswerMode('stream');
    void streaming.start(value ?? question, filters);
  };

  const openCitation = (citation: Citation) => {
    openTranscript({
      callId: citation.call_id,
      turnStart: citation.turn_start,
      turnEnd: citation.turn_end,
    });
  };

  return (
    <div className="content-max ask-page">
      <Card padding="md">
        <PatientFilterPanel filters={filters} onChange={setFilters} />

        <QuestionComposer
          question={question}
          loading={loading}
          streaming={streaming.phase === 'retrieving' || streaming.phase === 'generating'}
          onQuestionChange={setQuestion}
          onAsk={handleAsk}
          onAskStream={handleAskStream}
          onCancelStream={streaming.cancel}
        />

        {error ? <div className="error" role="alert">{error}</div> : null}

        {answerMode === 'sync' && answer ? (
          <>
            <AnswerCard
              answer={answer}
              onOpenWhyThisAnswer={
                health?.developer_mode && answer.request_id ? () => setWhyRequestId(answer.request_id!) : undefined
              }
            />
            <SourceList citations={answer.citations} onOpenCitation={openCitation} />
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
            onOpenCitation={openCitation}
          />
        ) : null}
      </Card>
      <WhyThisAnswerDrawer requestId={whyRequestId} onClose={() => setWhyRequestId(null)} />
    </div>
  );
}
