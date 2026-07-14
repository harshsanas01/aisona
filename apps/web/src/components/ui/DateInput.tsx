import type { InputHTMLAttributes } from 'react';
import { useId } from 'react';

interface DateInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function DateInput({ label, id, className = '', ...rest }: DateInputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const input = <input id={inputId} type="date" className={`input ${className}`.trim()} {...rest} />;

  if (!label) return input;
  return (
    <div className="field">
      <label className="field-label" htmlFor={inputId}>{label}</label>
      {input}
    </div>
  );
}
