import type { InputHTMLAttributes, ReactNode } from 'react';
import { useId } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  icon?: ReactNode;
}

export function Input({ label, hint, error, icon, id, className = '', ...rest }: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const input = (
    <input
      id={inputId}
      className={`input ${className}`.trim()}
      aria-invalid={Boolean(error) || undefined}
      aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
      {...rest}
    />
  );

  if (!label && !hint && !error && !icon) return input;

  return (
    <div className="field">
      {label ? <label className="field-label" htmlFor={inputId}>{label}</label> : null}
      {icon ? <div className="input-with-icon">{icon}{input}</div> : input}
      {error ? <span id={`${inputId}-error`} className="field-error">{error}</span> : hint ? (
        <span id={`${inputId}-hint`} className="field-hint">{hint}</span>
      ) : null}
    </div>
  );
}
