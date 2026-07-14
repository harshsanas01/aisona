import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PatientFilterPanel } from '../PatientFilterPanel';
import * as api from '../../../services/api';

vi.mock('../../../services/api', async () => {
  const actual = await vi.importActual<typeof api>('../../../services/api');
  return { ...actual, getPatients: vi.fn().mockResolvedValue([]) };
});

describe('PatientFilterPanel', () => {
  it('starts collapsed with no active-filter pills', () => {
    render(<PatientFilterPanel filters={{ patientId: null, startDate: null, endDate: null }} onChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: /^Filters/ })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/Rosa Kim/)).not.toBeInTheDocument();
  });

  it('expands to reveal patient/date fields on toggle', async () => {
    const user = userEvent.setup();
    render(<PatientFilterPanel filters={{ patientId: null, startDate: null, endDate: null }} onChange={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: /^Filters/ }));
    expect(screen.getByLabelText('Patient')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toBeInTheDocument();
    expect(screen.getByLabelText('To')).toBeInTheDocument();
  });

  it('shows a removable pill per active filter and clears one via its remove control', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PatientFilterPanel
        filters={{ patientId: null, startDate: '2026-06-01', endDate: null }}
        onChange={onChange}
      />,
    );
    expect(screen.getByText('From 2026-06-01')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Remove filter' }));
    expect(onChange).toHaveBeenCalledWith({ patientId: null, startDate: null, endDate: null });
  });

  it('Clear all resets every filter at once', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PatientFilterPanel
        filters={{ patientId: 'p_001', startDate: '2026-06-01', endDate: '2026-06-30' }}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Clear all' }));
    expect(onChange).toHaveBeenCalledWith({ patientId: null, startDate: null, endDate: null });
  });
});
