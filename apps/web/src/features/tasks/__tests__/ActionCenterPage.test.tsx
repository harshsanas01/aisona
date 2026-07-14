import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ActionCenterPage } from '../ActionCenterPage';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';
import { ToastProvider } from '../../../components/ui/Toast';

vi.mock('../../../services/api', () => ({
  getPatients: vi.fn().mockResolvedValue([
    { id: 'P-1001', name: 'Margaret Chen', age: 78 },
    { id: 'P-1007', name: 'Betty Park', age: 82 },
  ]),
  listTasks: vi.fn(),
  createTask: vi.fn(),
  getTask: vi.fn(),
  updateTask: vi.fn(),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
}));

import { createTask, listTasks } from '../../../services/api';

const OPEN_TASK = {
  task_id: 'task-1',
  title: 'Follow up: Home safety concern observed',
  description: 'Coordinator follow-up suggested based on an observed transcript event.',
  patient_id: 'P-1007',
  priority: 'high',
  status: 'open',
  category: 'home_safety',
  is_suggested: true,
  created_by: 'system',
  source_event_id: 'evt-1',
  source_call_id: 'call_008',
  source_turn_start: 4,
  source_turn_end: 4,
  assignee: null,
  due_date: null,
  completed_at: null,
  created_at: '2026-01-01T00:00:00+00:00',
  updated_at: '2026-01-01T00:00:00+00:00',
};

function renderPage() {
  return render(
    <ToastProvider>
      <TranscriptDrawerProvider>
        <MemoryRouter>
          <ActionCenterPage />
        </MemoryRouter>
        <TranscriptDrawer />
      </TranscriptDrawerProvider>
    </ToastProvider>,
  );
}

describe('ActionCenterPage', () => {
  it('lists tasks with their status/priority badges and a Suggested badge for system-generated tasks', async () => {
    vi.mocked(listTasks).mockResolvedValue([OPEN_TASK]);

    renderPage();

    expect(await screen.findByText('Follow up: Home safety concern observed')).toBeInTheDocument();
    expect(screen.getByText('Suggested')).toBeInTheDocument();
    expect(screen.getAllByText('Open').length).toBeGreaterThan(0);
    expect(screen.getAllByText('High').length).toBeGreaterThan(0);
  });

  it('shows an empty state when there are no tasks', async () => {
    vi.mocked(listTasks).mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText('No tasks match')).toBeInTheDocument();
  });

  it('switching to board view groups tasks by status column', async () => {
    vi.mocked(listTasks).mockResolvedValue([OPEN_TASK]);

    const user = userEvent.setup();
    renderPage();

    await screen.findByText('Follow up: Home safety concern observed');
    await user.click(screen.getByRole('button', { name: /Board/ }));

    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Dismissed')).toBeInTheDocument();
  });

  it('creating a task opens the modal and calls createTask on submit', async () => {
    vi.mocked(listTasks).mockResolvedValue([]);
    vi.mocked(createTask).mockResolvedValue({ ...OPEN_TASK, task_id: 'task-2' });

    const user = userEvent.setup();
    renderPage();

    await screen.findByText('No tasks match');
    await user.click(screen.getByRole('button', { name: /New task/ }));

    await user.type(screen.getByLabelText('Title'), 'Check in on Betty');
    await user.type(screen.getByLabelText('Description'), 'Call to confirm grab bars were installed.');
    await user.selectOptions(screen.getByLabelText('Patient'), 'P-1007');

    await user.click(screen.getByRole('button', { name: 'Create task' }));

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Check in on Betty',
        patient_id: 'P-1007',
      }));
    });
  });
});
