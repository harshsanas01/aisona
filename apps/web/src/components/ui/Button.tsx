import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: 'sm' | 'md';
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  block?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  leftIcon,
  rightIcon,
  block = false,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    'btn',
    `btn-${variant}`,
    size === 'sm' ? 'btn-sm' : '',
    block ? 'btn-block' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="btn-spinner" aria-hidden="true" /> : leftIcon}
      {children}
      {!loading ? rightIcon : null}
    </button>
  );
}
