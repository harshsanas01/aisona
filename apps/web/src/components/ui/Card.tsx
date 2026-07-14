import type { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

export function Card({ padding = 'md', interactive = false, className = '', ...rest }: CardProps) {
  const classes = ['card', `card-pad-${padding}`, interactive ? 'card-interactive' : '', className]
    .filter(Boolean)
    .join(' ');
  return <div className={classes} {...rest} />;
}
