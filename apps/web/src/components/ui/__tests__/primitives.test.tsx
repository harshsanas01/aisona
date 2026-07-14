import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Button } from '../Button';
import { Badge } from '../Badge';
import { FilterChip } from '../FilterChip';
import { EmptyState } from '../EmptyState';

describe('Button', () => {
  it('fires onClick and disables while loading', async () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button onClick={onClick}>Ask</Button>);
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(onClick).toHaveBeenCalledOnce();

    rerender(<Button onClick={onClick} loading>Ask</Button>);
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
  });
});

describe('Badge', () => {
  it('renders its tone class and content', () => {
    render(<Badge tone="success">Answerable</Badge>);
    const badge = screen.getByText('Answerable');
    expect(badge).toHaveClass('badge-success');
  });
});

describe('FilterChip', () => {
  it('calls onRemove without triggering onClick', async () => {
    const onClick = vi.fn();
    const onRemove = vi.fn();
    render(<FilterChip active onClick={onClick} onRemove={onRemove}>Margaret Chen</FilterChip>);
    await userEvent.click(screen.getByRole('button', { name: 'Remove filter' }));
    expect(onRemove).toHaveBeenCalledOnce();
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe('EmptyState', () => {
  it('announces itself as a status region', () => {
    render(<EmptyState title="No transcript selected" description="Pick a source card." />);
    expect(screen.getByRole('status')).toHaveTextContent('No transcript selected');
  });
});
