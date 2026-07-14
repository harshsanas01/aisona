import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AskPage } from '../AskPage';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';

vi.mock('../../../services/api', () => ({
  askQuestion: vi.fn(),
  streamAskQuestion: vi.fn(),
  getPatients: vi.fn().mockResolvedValue([]),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
}));

import { askQuestion, getCall } from '../../../services/api';

function renderAskPage() {
  return render(
    <TranscriptDrawerProvider>
      <AskPage />
      <TranscriptDrawer />
    </TranscriptDrawerProvider>,
  );
}

describe('AskPage', () => {
  it('renders an answerable response with its source card', async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'Which participants reported feeling dizzy in June?',
      answer: "Based on Frank Delgado's call: dizziness noted.",
      answerable: true,
      confidence: 'high',
      citations: [{
        call_id: 'call_004', patient_id: 'p_004', patient_name: 'Frank Delgado',
        date: '2026-05-29', turn_start: 7, turn_end: 10, quote: 'feeling a little dizzy',
      }],
      retrieval_debug: { mode: 'hybrid', candidate_count: 3 },
      filters: { patient_id: null, start_date: null, end_date: null },
    });

    const user = userEvent.setup();
    renderAskPage();

    await user.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByText('Answerable')).toBeInTheDocument();
    expect(screen.getByText('high confidence')).toBeInTheDocument();
    expect(screen.getByText('Frank Delgado')).toBeInTheDocument();
  });

  it('gives the unanswerable state distinct styling, not the answerable one', async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'What is the weather on Mars?',
      answer: 'The care-call transcripts do not contain enough evidence to answer this question.',
      answerable: false,
      confidence: 'low',
      citations: [],
      retrieval_debug: { mode: 'hybrid', candidate_count: 0 },
      filters: { patient_id: null, start_date: null, end_date: null },
    });

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    const card = (await screen.findByText('Not enough evidence')).closest('.answer-result-card');
    expect(card).toHaveClass('is-unanswerable');
    expect(card).not.toHaveClass('is-answerable');
  });

  it('opens the transcript drawer at the cited turn range when a source card is clicked', async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'q', answer: 'a', answerable: true, confidence: 'high',
      citations: [{
        call_id: 'call_004', patient_id: 'p_004', patient_name: 'Frank Delgado',
        date: '2026-05-29', turn_start: 7, turn_end: 10, quote: 'quote text',
      }],
      retrieval_debug: { mode: 'hybrid', candidate_count: 1 },
      filters: { patient_id: null, start_date: null, end_date: null },
    });
    vi.mocked(getCall).mockResolvedValue({
      call_id: 'call_004', date: '2026-05-29',
      patient: { id: 'p_004', name: 'Frank Delgado', age: 81 },
      duration_seconds: 356,
      turns: Array.from({ length: 10 }, (_, i) => ({ turn_number: i + 1, speaker: 'assistant', text: `turn ${i + 1}` })),
    });

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));
    await user.click(await screen.findByRole('button', { name: /Open transcript for Frank Delgado/ }));

    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
    expect(within(screen.getByRole('dialog')).getAllByText('Frank Delgado').length).toBeGreaterThan(0);
  });
});

function within(element: HTMLElement) {
  // Local helper so we don't need an extra import purely for this one lookup.
  return { getAllByText: (text: string) => Array.from(element.querySelectorAll('*')).filter((el) => el.textContent === text) };
}
