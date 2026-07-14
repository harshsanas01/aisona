import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BriefsPage } from '../BriefsPage';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';
import { ToastProvider } from '../../../components/ui/Toast';

vi.mock('../../../services/api', () => ({
  getPatients: vi.fn().mockResolvedValue([{ id: 'P-1001', name: 'Margaret Chen', age: 78 }]),
  listBriefs: vi.fn().mockResolvedValue([]),
  generateBrief: vi.fn(),
  regenerateBrief: vi.fn(),
  getBrief: vi.fn(),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
}));

import { generateBrief } from '../../../services/api';

const SAMPLE_BRIEF = {
  brief_id: 'brief-1',
  brief_type: 'weekly',
  start_date: '2026-06-01',
  end_date: '2026-06-07',
  patient_id: null,
  include_resolved: false,
  model_version: 'deterministic',
  prompt_version: 'v1',
  generated_at: '2026-06-08T00:00:00+00:00',
  created_at: '2026-06-08T00:00:00+00:00',
  updated_at: '2026-06-08T00:00:00+00:00',
  bullets: [
    {
      bullet_id: 'bul-1',
      section: 'high_attention',
      patient_id: 'P-1001',
      patient_name: 'Margaret Chen',
      summary: 'Observed pattern: something notable happened.',
      related_timeline_event_ids: ['evt-1'],
      related_pattern_id: 'pat-1',
      related_task_id: null,
      evidence: [{ timeline_event_id: 'evt-1', call_id: 'call_009', turn_start: 2, turn_end: 2, quote: 'a quote' }],
    },
  ],
};

function renderPage() {
  return render(
    <ToastProvider>
      <TranscriptDrawerProvider>
        <BriefsPage />
        <TranscriptDrawer />
      </TranscriptDrawerProvider>
    </ToastProvider>,
  );
}

describe('BriefsPage', () => {
  it('generating a brief calls generateBrief with the selected type and renders the result', async () => {
    vi.mocked(generateBrief).mockResolvedValue(SAMPLE_BRIEF);

    const user = userEvent.setup();
    renderPage();

    await screen.findByText('No brief generated yet');
    await user.click(screen.getByRole('button', { name: /Generate brief/ }));

    await waitFor(() => {
      expect(generateBrief).toHaveBeenCalledWith(expect.objectContaining({ type: 'weekly' }));
    });

    // "Weekly Care Brief" appears twice: once in the normal header, once in
    // the print-only header (hidden on screen, shown only via @media print).
    expect((await screen.findAllByText('Weekly Care Brief')).length).toBeGreaterThan(0);
    expect(screen.getByText(/Observed pattern: something notable happened/)).toBeInTheDocument();
    expect(screen.getAllByText(/model: deterministic/).length).toBeGreaterThan(0);
  });

  it('shows the empty state before any brief has been generated', async () => {
    renderPage();
    expect(await screen.findByText('No brief generated yet')).toBeInTheDocument();
  });
});
