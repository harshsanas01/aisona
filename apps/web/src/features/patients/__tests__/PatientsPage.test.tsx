import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PatientsPage } from '../PatientsPage';

vi.mock('../../../services/api', () => ({
  getPatients: vi.fn(),
  getPatient: vi.fn(),
}));

import { getPatient, getPatients } from '../../../services/api';

describe('PatientsPage', () => {
  it('lists patients with their timeline summary counts', async () => {
    vi.mocked(getPatients).mockResolvedValue([{ id: 'P-1008', name: 'Samuel Rivera', age: 80 }]);
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 2, unreviewed_event_count: 1,
    });

    render(<MemoryRouter><PatientsPage /></MemoryRouter>);

    expect(await screen.findByText('Samuel Rivera')).toBeInTheDocument();
    expect(screen.getByText('2 timeline events')).toBeInTheDocument();
    expect(screen.getByText('1 unreviewed')).toBeInTheDocument();
  });

  it('filters the roster by search text', async () => {
    vi.mocked(getPatients).mockResolvedValue([
      { id: 'P-1001', name: 'Margaret Chen', age: 78 },
      { id: 'P-1008', name: 'Samuel Rivera', age: 80 },
    ]);
    vi.mocked(getPatient).mockImplementation(async (id: string) => ({
      id, name: id === 'P-1001' ? 'Margaret Chen' : 'Samuel Rivera', age: 78, timeline_event_count: 0, unreviewed_event_count: 0,
    }));

    const user = userEvent.setup();
    render(<MemoryRouter><PatientsPage /></MemoryRouter>);

    await screen.findByText('Margaret Chen');
    await user.type(screen.getByLabelText('Search patients'), 'Samuel');

    expect(screen.queryByText('Margaret Chen')).not.toBeInTheDocument();
    expect(screen.getByText('Samuel Rivera')).toBeInTheDocument();
  });
});
