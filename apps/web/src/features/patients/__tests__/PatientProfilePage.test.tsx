import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PatientProfilePage } from '../PatientProfilePage';
import { RoleProvider } from '../../../app/RoleContext';
import { TranscriptDrawerProvider } from '../../transcript-viewer/TranscriptDrawerContext';
import { TranscriptDrawer } from '../../transcript-viewer/TranscriptDrawer';
import { ToastProvider } from '../../../components/ui/Toast';

vi.mock('../../../services/api', () => ({
  getPatient: vi.fn(),
  getPatientTimeline: vi.fn(),
  rebuildPatientTimeline: vi.fn(),
  updateTimelineEvent: vi.fn(),
  getPatientPatterns: vi.fn().mockResolvedValue([]),
  rebuildPatientPatterns: vi.fn(),
  updatePatternReviewedStatus: vi.fn(),
  getPatientPersonMentions: vi.fn().mockResolvedValue([]),
  rebuildPatientPersonMentions: vi.fn(),
  updatePersonMention: vi.fn(),
  suggestTaskFromEvent: vi.fn(),
  getCall: vi.fn(),
  getSafetyEvents: vi.fn().mockResolvedValue([]),
  submitFeedback: vi.fn().mockResolvedValue({}),
  ROLE_STORAGE_KEY: 'carecall.role',
}));

import {
  getPatient, getPatientPatterns, getPatientPersonMentions, getPatientTimeline, submitFeedback,
  suggestTaskFromEvent, updatePatternReviewedStatus, updatePersonMention, updateTimelineEvent,
} from '../../../services/api';

const GUS_EVENT = {
  event_id: 'evt-call_021-2-home_safety_concern',
  patient_id: 'P-1008',
  event_type: 'home_safety_concern',
  title: 'Home safety concern observed',
  description: 'Observed pattern: a home-safety concern was reported in the transcript. Requires staff review.',
  observed_date: '2026-06-23',
  source_call_id: 'call_021',
  source_turn_start: 2,
  source_turn_end: 2,
  quote: 'Doing fine myself, but poor Gus next door had a rough weekend. He tripped and sprained his wrist.',
  confidence: 'medium',
  extraction_method: 'deterministic',
  review_status: 'unreviewed',
  created_at: '2026-06-23T00:00:00+00:00',
  updated_at: '2026-06-23T00:00:00+00:00',
};

const GUS_MENTION = {
  mention_id: 'pm-call_021-2-neighbor',
  patient_id: 'P-1008',
  source_call_id: 'call_021',
  source_turn: 2,
  quote: 'Doing fine myself, but poor Gus next door had a rough weekend.',
  role_label: 'neighbor',
  relationship_type: 'neighbor',
  mentioned_name: 'Gus',
  confidence: 'medium',
  extraction_method: 'deterministic',
  review_status: 'unreviewed',
  created_at: '2026-06-23T00:00:00+00:00',
  updated_at: '2026-06-23T00:00:00+00:00',
};

const GUS_SON_MENTION = {
  mention_id: 'pm-call_021-4-son',
  patient_id: 'P-1008',
  source_call_id: 'call_021',
  source_turn: 4,
  quote: "His son drove him to urgent care. It's wrapped up, nothing broken.",
  role_label: 'son',
  relationship_type: 'unknown',
  mentioned_name: null,
  confidence: 'medium',
  extraction_method: 'deterministic',
  review_status: 'unreviewed',
  created_at: '2026-06-23T00:00:00+00:00',
  updated_at: '2026-06-23T00:00:00+00:00',
};

const HOME_SAFETY_PATTERN = {
  pattern_id: 'pat-P-1008-first_occurrence-call_021',
  patient_id: 'P-1008',
  pattern_type: 'first_occurrence',
  title: 'First reported: a home-safety concern',
  summary: 'Observed pattern: a home-safety concern was first reported on 2026-06-23 (call call_021). Requires staff review.',
  status: 'active',
  severity: 'informational',
  first_observed_date: '2026-06-23',
  latest_observed_date: '2026-06-23',
  related_timeline_event_ids: ['evt-call_021-2-home_safety_concern'],
  related_call_ids: ['call_021'],
  evidence: [{
    timeline_event_id: 'evt-call_021-2-home_safety_concern', call_id: 'call_021', turn_start: 2, turn_end: 2,
    quote: 'Doing fine myself, but poor Gus next door had a rough weekend.',
  }],
  detector_version: 'v1',
  reviewed_status: 'unreviewed',
  created_at: '2026-06-23T00:00:00+00:00',
  updated_at: '2026-06-23T00:00:00+00:00',
};

function renderProfile() {
  return render(
    <RoleProvider>
      <ToastProvider>
        <TranscriptDrawerProvider>
          <MemoryRouter initialEntries={['/patients/P-1008']}>
            <Routes>
              <Route path="/patients/:patientId" element={<PatientProfilePage />} />
            </Routes>
          </MemoryRouter>
          <TranscriptDrawer />
        </TranscriptDrawerProvider>
      </ToastProvider>
    </RoleProvider>,
  );
}

describe('PatientProfilePage', () => {
  it('renders the summary header, the not-diagnosis disclaimer, and a timeline event without attributing Gus to Samuel', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);

    renderProfile();

    expect(await screen.findByText('Samuel Rivera')).toBeInTheDocument();
    expect(screen.getByText(/Observed transcript events - not diagnosis/)).toBeInTheDocument();
    expect(screen.getByText(/Gus/)).toBeInTheDocument();
    expect(screen.queryByText(/poor Samuel/)).not.toBeInTheDocument();
  });

  it('shows a not-found state for an unknown patient', async () => {
    vi.mocked(getPatient).mockResolvedValue(null);
    vi.mocked(getPatientTimeline).mockResolvedValue([]);

    renderProfile();

    expect(await screen.findByText('Patient not found')).toBeInTheDocument();
  });

  it('confirming an event calls updateTimelineEvent with review_status confirmed', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);
    vi.mocked(updateTimelineEvent).mockResolvedValue({ ...GUS_EVENT, review_status: 'confirmed' });

    const user = userEvent.setup();
    renderProfile();

    await screen.findByText('Samuel Rivera');
    await user.click(screen.getByRole('button', { name: /Confirm/ }));

    await waitFor(() => {
      expect(updateTimelineEvent).toHaveBeenCalledWith(GUS_EVENT.event_id, { review_status: 'confirmed' });
    });
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        target_type: 'timeline_event', target_id: GUS_EVENT.event_id, category: 'confirm', actor: 'coordinator',
      });
    });
  });

  it('renders the Observed patterns section with the not-a-clinical-conclusion disclaimer and evidence trail', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 1, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);
    vi.mocked(getPatientPatterns).mockResolvedValue([HOME_SAFETY_PATTERN]);
    vi.mocked(updatePatternReviewedStatus).mockResolvedValue({ ...HOME_SAFETY_PATTERN, reviewed_status: 'confirmed' });

    const user = userEvent.setup();
    renderProfile();

    expect(await screen.findByText('Observed patterns')).toBeInTheDocument();
    expect(screen.getByText(/Pattern detected from transcript history - not a clinical conclusion/)).toBeInTheDocument();
    expect(screen.getByText('First reported: a home-safety concern')).toBeInTheDocument();
    expect(screen.getByText(/Open call_021 \(turn 2\)/)).toBeInTheDocument();

    const patternConfirmButtons = screen.getAllByRole('button', { name: /Confirm/ });
    await user.click(patternConfirmButtons[patternConfirmButtons.length - 1]);

    await waitFor(() => {
      expect(updatePatternReviewedStatus).toHaveBeenCalledWith(HOME_SAFETY_PATTERN.pattern_id, 'confirmed');
    });
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        target_type: 'pattern', target_id: HOME_SAFETY_PATTERN.pattern_id, category: 'confirm', actor: 'coordinator',
      });
    });
  });

  it('suggesting a task from a timeline event calls suggestTaskFromEvent with the event id', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 0, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);
    vi.mocked(suggestTaskFromEvent).mockResolvedValue({ task_id: 'task-1' });

    const user = userEvent.setup();
    renderProfile();

    await screen.findByText('Samuel Rivera');
    await user.click(screen.getByRole('button', { name: /Suggest task/ }));

    await waitFor(() => {
      expect(suggestTaskFromEvent).toHaveBeenCalledWith(GUS_EVENT.event_id);
    });
  });

  it('renders People mentioned with Gus as neighbor, never family or participant', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 0, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);
    vi.mocked(getPatientPersonMentions).mockResolvedValue([GUS_MENTION, GUS_SON_MENTION]);

    renderProfile();

    expect(await screen.findByText('People mentioned')).toBeInTheDocument();
    expect(screen.getByText('Gus')).toBeInTheDocument();
    expect(screen.getAllByText('Neighbor').length).toBeGreaterThan(0);
    expect(screen.getByText('Unclear - needs review')).toBeInTheDocument();
  });

  it('confirming a person mention calls updatePersonMention and submits feedback', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 0, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([]);
    vi.mocked(getPatientPersonMentions).mockResolvedValue([GUS_MENTION]);
    vi.mocked(updatePersonMention).mockResolvedValue({ ...GUS_MENTION, review_status: 'confirmed' });

    const user = userEvent.setup();
    renderProfile();

    await screen.findByText('People mentioned');
    const confirmButtons = screen.getAllByRole('button', { name: /Confirm/ });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(updatePersonMention).toHaveBeenCalledWith(GUS_MENTION.mention_id, {
        review_status: 'confirmed', corrected_relationship_type: undefined, corrected_name: undefined,
      });
    });
    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith({
        target_type: 'person_mention', target_id: GUS_MENTION.mention_id, category: 'confirm', actor: 'coordinator',
      });
    });
  });

  it('lets a coordinator correct an unknown mention to a specific relationship type', async () => {
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 0, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([]);
    vi.mocked(getPatientPersonMentions).mockResolvedValue([GUS_SON_MENTION]);
    vi.mocked(updatePersonMention).mockResolvedValue({
      ...GUS_SON_MENTION, relationship_type: 'neighbor', review_status: 'corrected',
    });

    const user = userEvent.setup();
    renderProfile();

    await screen.findByText('People mentioned');
    await user.selectOptions(screen.getByLabelText(`Correct relationship for ${GUS_SON_MENTION.mention_id}`), 'neighbor');
    await user.click(screen.getByRole('button', { name: 'Save correction' }));

    await waitFor(() => {
      expect(updatePersonMention).toHaveBeenCalledWith(GUS_SON_MENTION.mention_id, {
        review_status: 'corrected', corrected_relationship_type: 'neighbor', corrected_name: undefined,
      });
    });
  });

  it('disables review actions for the viewer role but still allows viewing', async () => {
    localStorage.setItem('carecall.role', 'viewer');
    vi.mocked(getPatient).mockResolvedValue({
      id: 'P-1008', name: 'Samuel Rivera', age: 80, timeline_event_count: 1, unreviewed_event_count: 1,
      pattern_count: 1, attention_pattern_count: 0,
    });
    vi.mocked(getPatientTimeline).mockResolvedValue([GUS_EVENT]);
    vi.mocked(getPatientPatterns).mockResolvedValue([HOME_SAFETY_PATTERN]);
    vi.mocked(getPatientPersonMentions).mockResolvedValue([GUS_MENTION]);

    renderProfile();

    await screen.findByText('Samuel Rivera');
    const confirmButtons = screen.getAllByRole('button', { name: /Confirm/ });
    expect(confirmButtons.length).toBeGreaterThan(0);
    for (const button of confirmButtons) {
      expect(button).toBeDisabled();
    }

    localStorage.removeItem('carecall.role');
  });
});
