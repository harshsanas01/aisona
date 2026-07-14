import { useState, type KeyboardEvent } from 'react';
import {
  AlertTriangle, Moon, Pill, Sparkles, Waves, Wind, X,
} from 'lucide-react';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';

const QUESTION_MAX_LENGTH = 500;

const sampleQuestions = [
  { text: 'What new medication did Margaret Chen start?', icon: Pill },
  { text: 'Which participants reported feeling dizzy in June?', icon: Waves },
  { text: 'Who has been having trouble sleeping?', icon: Moon },
  { text: 'Has any participant fallen recently?', icon: AlertTriangle },
  { text: 'What happened with Dorothy’s cough?', icon: Wind },
];

interface QuestionComposerProps {
  question: string;
  loading: boolean;
  streaming: boolean;
  onQuestionChange: (value: string) => void;
  onAsk: (value?: string) => void;
  onAskStream: (value?: string) => void;
  onCancelStream: () => void;
}

export function QuestionComposer({
  question,
  loading,
  streaming,
  onQuestionChange,
  onAsk,
  onAskStream,
  onCancelStream,
}: QuestionComposerProps) {
  const [focused, setFocused] = useState(false);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      onAsk();
    }
  };

  return (
    <div className="composer">
      <div className="composer-label-row">
        <Sparkles size={15} className="composer-icon" aria-hidden="true" />
        <label className="field-label" htmlFor="question">Question</label>
      </div>
      <Textarea
        id="question"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value.slice(0, QUESTION_MAX_LENGTH))}
        onKeyDown={handleKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        rows={4}
        maxLength={QUESTION_MAX_LENGTH}
        showCount
        placeholder="Ask about symptoms, medications, missed rides, or other care concerns"
        hint={focused ? 'Ctrl/Cmd + Enter to ask' : undefined}
      />

      <div className="sample-questions">
        {sampleQuestions.map(({ text, icon: Icon }) => (
          <button key={text} type="button" className="sample-chip" onClick={() => { onQuestionChange(text); onAsk(text); }}>
            <Icon size={13} aria-hidden="true" />
            {text}
          </button>
        ))}
      </div>

      <div className="ask-buttons">
        <Button onClick={() => onAsk()} loading={loading}>Ask</Button>
        <Button variant="secondary" onClick={() => onAskStream()} loading={streaming}>
          {streaming ? 'Streaming…' : 'Ask (stream)'}
        </Button>
        {streaming ? (
          <Button variant="ghost" leftIcon={<X size={14} />} onClick={onCancelStream}>Cancel</Button>
        ) : null}
      </div>
    </div>
  );
}
