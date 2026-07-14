import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RetrievalLabPage } from '../RetrievalLabPage';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';

vi.mock('../../../services/api', () => ({
  compareRetrievalModes: vi.fn(),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
}));

import { compareRetrievalModes, getCall } from '../../../services/api';

function renderPage() {
  return render(
    <TranscriptDrawerProvider>
      <RetrievalLabPage />
      <TranscriptDrawer />
    </TranscriptDrawerProvider>,
  );
}

const MOCK_RESULTS = [
  {
    mode: 'lexical', lexical_weight: 1, semantic_weight: 0, reranked: false,
    candidates: [{
      chunk_id: 'c1', call_id: 'call_003', patient_id: 'P-1001', patient_name: 'Margaret Chen',
      date: '2026-05-28', turn_start: 1, turn_end: 4, quote: 'lisinopril quote', score: 0.9,
    }],
  },
  {
    mode: 'semantic', lexical_weight: 0, semantic_weight: 1, reranked: false,
    candidates: [],
  },
  {
    mode: 'hybrid', lexical_weight: 0.45, semantic_weight: 0.55, reranked: false,
    candidates: [{
      chunk_id: 'c1', call_id: 'call_003', patient_id: 'P-1001', patient_name: 'Margaret Chen',
      date: '2026-05-28', turn_start: 1, turn_end: 4, quote: 'lisinopril quote', score: 0.8,
    }],
  },
  {
    mode: 'hybrid_rerank', lexical_weight: 0.45, semantic_weight: 0.55, reranked: true,
    candidates: [{
      chunk_id: 'c1', call_id: 'call_003', patient_id: 'P-1001', patient_name: 'Margaret Chen',
      date: '2026-05-28', turn_start: 1, turn_end: 4, quote: 'lisinopril quote', score: 0.85,
    }],
  },
];

describe('RetrievalLabPage', () => {
  it('runs a comparison and renders all four mode cards', async () => {
    vi.mocked(compareRetrievalModes).mockResolvedValue(MOCK_RESULTS);

    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: /Compare modes/ }));

    expect(await screen.findByText('Lexical only')).toBeInTheDocument();
    expect(screen.getByText('Semantic only')).toBeInTheDocument();
    expect(screen.getByText('Hybrid')).toBeInTheDocument();
    expect(screen.getByText('Hybrid + rerank')).toBeInTheDocument();
    expect(screen.getByText('reranked')).toBeInTheDocument();
    expect(screen.getByText('No candidates')).toBeInTheDocument();
  });

  it('opens the transcript drawer at the cited turn when a candidate is clicked', async () => {
    vi.mocked(compareRetrievalModes).mockResolvedValue(MOCK_RESULTS);
    vi.mocked(getCall).mockResolvedValue({
      call_id: 'call_003', date: '2026-05-28',
      patient: { id: 'P-1001', name: 'Margaret Chen', age: 82 },
      duration_seconds: 300,
      turns: Array.from({ length: 10 }, (_, i) => ({ turn_number: i + 1, speaker: 'assistant', text: `turn ${i + 1}` })),
    });

    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: /Compare modes/ }));

    const evidenceButtons = await screen.findAllByText(/Open call_003 \(turn 1\)/);
    await user.click(evidenceButtons[0]);

    await waitFor(() => {
      expect(getCall).toHaveBeenCalledWith('call_003');
    });
  });

  it('shows an error message when the comparison request fails', async () => {
    vi.mocked(compareRetrievalModes).mockRejectedValue(new Error('The Retrieval Comparison Lab is only available in developer/admin mode'));

    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: /Compare modes/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('developer/admin mode');
  });
});
