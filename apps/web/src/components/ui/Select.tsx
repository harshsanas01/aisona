import type { SelectHTMLAttributes } from 'react';
import { useId } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({ label, options, placeholder, id, className = '', ...rest }: SelectProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const select = (
    <select id={selectId} className={`select ${className}`.trim()} {...rest}>
      {placeholder ? <option value="">{placeholder}</option> : null}
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  );

  if (!label) return select;
  return (
    <div className="field">
      <label className="field-label" htmlFor={selectId}>{label}</label>
      {select}
    </div>
  );
}
