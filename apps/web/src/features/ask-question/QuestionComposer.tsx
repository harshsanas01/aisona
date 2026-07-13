const sampleQuestions = [
  'What new medication did Margaret Chen start?',
  'Which participants reported feeling dizzy in June?',
  'Who has been having trouble sleeping?',
  'Has any participant fallen recently?',
  'What happened with Dorothy’s cough?',
];

interface QuestionComposerProps {
  question: string;
  loading: boolean;
  onQuestionChange: (value: string) => void;
  onAsk: (value?: string) => void;
}

export function QuestionComposer({ question, loading, onQuestionChange, onAsk }: QuestionComposerProps) {
  return (
    <>
      <label className="field-label" htmlFor="question">Question</label>
      <textarea
        id="question"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        rows={4}
        placeholder="Ask about symptoms, medications, missed rides, or other care concerns"
      />
      <div className="sample-questions">
        {sampleQuestions.map((sample) => (
          <button key={sample} type="button" onClick={() => { onQuestionChange(sample); onAsk(sample); }}>
            {sample}
          </button>
        ))}
      </div>
      <button className="primary" onClick={() => onAsk()} disabled={loading}>
        {loading ? 'Asking…' : 'Ask'}
      </button>
    </>
  );
}
