import type { TextareaHTMLAttributes } from 'react';
import { useId } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  showCount?: boolean;
}

export function Textarea({
  label,
  hint,
  error,
  showCount = false,
  maxLength,
  value,
  id,
  className = '',
  ...rest
}: TextareaProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const length = typeof value === 'string' ? value.length : 0;

  return (
    <div className="field">
      {label ? <label className="field-label" htmlFor={fieldId}>{label}</label> : null}
      <textarea
        id={fieldId}
        className={`textarea ${className}`.trim()}
        maxLength={maxLength}
        value={value}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={hint ? `${fieldId}-hint` : undefined}
        {...rest}
      />
      <div className="field-hint" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span id={`${fieldId}-hint`}>{error ? <span className="field-error">{error}</span> : hint}</span>
        {showCount && maxLength ? (
          <span aria-live="polite">{length} / {maxLength}</span>
        ) : null}
      </div>
    </div>
  );
}
