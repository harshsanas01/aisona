import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AskPage } from '../AskPage';
import { RoleProvider } from '../../../app/RoleContext';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';

vi.mock('../../../services/api', () => ({
  askQuestion: vi.fn(),
  streamAskQuestion: vi.fn(),
  getPatients: vi.fn().mockResolvedValue([]),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
  getHealth: vi.fn().mockResolvedValue({ status: 'ok', calls_loaded: 21, retrieval_mode: 'hybrid' }),
  getAuditQuestion: vi.fn(),
  submitFeedback: vi.fn(),
  ROLE_STORAGE_KEY: 'carecall.role',
}));

import { askQuestion, getAuditQuestion, getCall, getHealth, submitFeedback } from '../../../services/api';

function renderAskPage() {
  return render(
    <RoleProvider>
      <TranscriptDrawerProvider>
        <AskPage />
        <TranscriptDrawer />
      </TranscriptDrawerProvider>
    </RoleProvider>,
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

  it('shows "Why this answer?" only in developer mode, and opens the audit drawer on click', async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: 'ok', calls_loaded: 21, retrieval_mode: 'hybrid', developer_mode: true,
    });
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'q', answer: 'a', answerable: true, confidence: 'high',
      citations: [],
      retrieval_debug: { mode: 'hybrid', candidate_count: 1 },
      filters: { patient_id: null, start_date: null, end_date: null },
      request_id: 'req-123',
    });
    vi.mocked(getAuditQuestion).mockResolvedValue({
      request_id: 'req-123', created_at: '2026-06-01T00:00:00+00:00', question_hash: 'abc',
      question_preview: null, filters: { patient_id: null, start_date: null, end_date: null },
      storage_mode: 'memory', retrieval_mode: 'hybrid', lexical_weight: 0.45, semantic_weight: 0.55,
      top_k: 8, relevance_threshold: 0.15, candidate_chunk_ids: ['call_004:1:2'],
      selected_evidence_ids: ['call_004:1:2'], answer_mode: 'mock', provider: 'mock', model_name: 'mock',
      prompt_version: 'v1', token_usage: null, latency_ms: 42, answerable: true, confidence: 'high',
      final_citation_call_ids: ['call_004'], grounding_checks: { citation_validation: true },
      fallback_used: false, error_category: null, feedback_summary: {},
    });

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    const whyButton = await screen.findByRole('button', { name: /Why this answer/ });
    await user.click(whyButton);

    expect(await screen.findByRole('heading', { name: 'Why this answer?' })).toBeInTheDocument();
    expect(await screen.findByText('citation validation: passed')).toBeInTheDocument();
  });

  it('submits thumbs-up feedback for the answer directly, with no modal', async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'q', answer: 'a', answerable: true, confidence: 'high',
      citations: [],
      retrieval_debug: { mode: 'hybrid', candidate_count: 1 },
      filters: { patient_id: null, start_date: null, end_date: null },
      request_id: 'req-456',
    });
    vi.mocked(submitFeedback).mockResolvedValue({});

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    const thumbsUp = await screen.findByRole('button', { name: 'This answer was correct' });
    await user.click(thumbsUp);

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        target_type: 'answer', target_id: 'req-456', category: 'correct', actor: 'coordinator',
      });
    });
    expect(await screen.findByText('Thanks for the feedback')).toBeInTheDocument();
  });

  it('opens a feedback modal on thumbs-down and submits the selected category', async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'q', answer: 'a', answerable: true, confidence: 'high',
      citations: [],
      retrieval_debug: { mode: 'hybrid', candidate_count: 1 },
      filters: { patient_id: null, start_date: null, end_date: null },
      request_id: 'req-789',
    });
    vi.mocked(submitFeedback).mockResolvedValue({});

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    const thumbsDown = await screen.findByRole('button', { name: 'This answer had a problem' });
    await user.click(thumbsDown);

    expect(await screen.findByRole('heading', { name: 'What was wrong with this answer?' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Submit feedback' }));

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({ target_type: 'answer', target_id: 'req-789', category: 'partially_correct' }),
      );
    });
    expect(await screen.findByText('Thanks for the feedback')).toBeInTheDocument();
  });

  it('disables thumbs up/down feedback for the viewer role', async () => {
    localStorage.setItem('carecall.role', 'viewer');
    vi.mocked(askQuestion).mockResolvedValue({
      question: 'q', answer: 'a', answerable: true, confidence: 'high',
      citations: [],
      retrieval_debug: { mode: 'hybrid', candidate_count: 1 },
      filters: { patient_id: null, start_date: null, end_date: null },
      request_id: 'req-999',
    });

    const user = userEvent.setup();
    renderAskPage();
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    const thumbsUp = await screen.findByRole('button', { name: 'This answer was correct' });
    const thumbsDown = screen.getByRole('button', { name: 'This answer had a problem' });
    expect(thumbsUp).toBeDisabled();
    expect(thumbsDown).toBeDisabled();

    localStorage.removeItem('carecall.role');
  });
});

function within(element: HTMLElement) {
  // Local helper so we don't need an extra import purely for this one lookup.
  return { getAllByText: (text: string) => Array.from(element.querySelectorAll('*')).filter((el) => el.textContent === text) };
}
