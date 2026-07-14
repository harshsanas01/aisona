import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArrowUpRight, CheckCircle2, Clock, ClipboardPlus, RotateCcw, ShieldQuestion, TrendingUp, Users, XCircle,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Select } from '../../components/ui/Select';
import { Input } from '../../components/ui/Input';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { useToast } from '../../components/ui/Toast';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import { usePatientTimeline } from './usePatientTimeline';
import { usePatientPatterns } from './usePatientPatterns';
import { usePatientPersonMentions } from './usePatientPersonMentions';
import { TIMELINE_EVENT_TYPE_META, reviewStatusLabel, timelineEventTypeMeta } from './timelineEventCategories';
import {
  patternReviewedStatusLabel,
  patternSeverityBadgeTone,
  patternSeverityLabel,
  patternStatusLabel,
  patternTypeLabel,
} from './patternMeta';
import { personMentionReviewStatusLabel, relationshipTypeBadgeTone, relationshipTypeLabel } from './personMentionMeta';
import { submitFeedback, suggestTaskFromEvent } from '../../services/api';
import { useRole } from '../../app/RoleContext';
import type { PatientPattern, PersonMention, TimelineEvent, TimelineReviewStatus } from '../../types';
import './patient-profile.css';

const REVIEW_DISABLED_TITLE = "Your current role (Viewer) can't review or correct records.";

const CORRECTABLE_RELATIONSHIP_TYPES = ['participant', 'family', 'neighbor', 'staff'];

const REVIEW_STATUSES: TimelineReviewStatus[] = ['unreviewed', 'confirmed', 'corrected', 'dismissed'];

// review_status/reviewed_status values ("confirmed"/"corrected"/"dismissed") use
// past-tense state names, while feedback categories ("confirm"/"correct"/"dismiss")
// name the reviewer's action - this maps one to the other.
const REVIEW_STATUS_TO_FEEDBACK_CATEGORY: Record<string, string> = {
  confirmed: 'confirm',
  corrected: 'correct',
  dismissed: 'dismiss',
};

export function PatientProfilePage() {
  const { patientId = '' } = useParams<{ patientId: string }>();
  const { patient, events, loading, rebuilding, error, notFound, rebuild, updateEvent } = usePatientTimeline(patientId);
  const {
    patterns, loading: patternsLoading, rebuilding: patternsRebuilding, error: patternsError,
    rebuild: rebuildPatterns, updateReviewedStatus,
  } = usePatientPatterns(patientId);
  const {
    mentions, loading: mentionsLoading, rebuilding: mentionsRebuilding, error: mentionsError,
    rebuild: rebuildMentions, updateReviewStatus: updateMentionReviewStatus,
  } = usePatientPersonMentions(patientId);
  const { open: openTranscript } = useTranscriptDrawer();
  const { hasPermission } = useRole();
  const canReview = hasPermission('review');
  const toast = useToast();

  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [reviewStatusFilter, setReviewStatusFilter] = useState('');
  const [correctionDrafts, setCorrectionDrafts] = useState<Record<string, { relationshipType: string; name: string }>>({});

  const filtered = useMemo(() => {
    return events
      .filter((e) => !eventTypeFilter || e.event_type === eventTypeFilter)
      .filter((e) => !reviewStatusFilter || e.review_status === reviewStatusFilter);
  }, [events, eventTypeFilter, reviewStatusFilter]);

  const unreviewedCount = events.filter((e) => e.review_status === 'unreviewed').length;

  const handleReview = async (event: TimelineEvent, status: TimelineReviewStatus) => {
    try {
      await updateEvent(event.event_id, { review_status: status });
      toast.show(`Marked as ${reviewStatusLabel(status).toLowerCase()}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update event', 'error');
      return;
    }
    submitFeedback({
      target_type: 'timeline_event',
      target_id: event.event_id,
      category: REVIEW_STATUS_TO_FEEDBACK_CATEGORY[status] ?? status,
      actor: 'coordinator',
    }).catch(() => {
      // Best-effort audit trail - the review itself already succeeded above.
    });
  };

  const handleRebuild = async () => {
    await rebuild();
    toast.show('Timeline rebuilt from transcripts');
  };

  const handlePatternReview = async (pattern: PatientPattern, status: string) => {
    try {
      await updateReviewedStatus(pattern.pattern_id, status);
      toast.show(`Marked as ${patternReviewedStatusLabel(status).toLowerCase()}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update pattern', 'error');
      return;
    }
    submitFeedback({
      target_type: 'pattern',
      target_id: pattern.pattern_id,
      category: REVIEW_STATUS_TO_FEEDBACK_CATEGORY[status] ?? status,
      actor: 'coordinator',
    }).catch(() => {
      // Best-effort audit trail - the review itself already succeeded above.
    });
  };

  const handleRebuildPatterns = async () => {
    await rebuildPatterns();
    toast.show('Patterns rebuilt from timeline events');
  };

  const handleMentionReview = async (
    mention: PersonMention, status: string, corrections?: { relationshipType?: string; name?: string },
  ) => {
    try {
      await updateMentionReviewStatus(mention.mention_id, status, corrections);
      toast.show(`Marked as ${personMentionReviewStatusLabel(status).toLowerCase()}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update person mention', 'error');
      return;
    }
    submitFeedback({
      target_type: 'person_mention',
      target_id: mention.mention_id,
      category: REVIEW_STATUS_TO_FEEDBACK_CATEGORY[status] ?? status,
      actor: 'coordinator',
    }).catch(() => {
      // Best-effort audit trail - the review itself already succeeded above.
    });
  };

  const handleSaveCorrection = (mention: PersonMention) => {
    const draft = correctionDrafts[mention.mention_id];
    if (!draft?.relationshipType) return;
    void handleMentionReview(mention, 'corrected', {
      relationshipType: draft.relationshipType,
      name: draft.name || undefined,
    });
  };

  const handleRebuildMentions = async () => {
    await rebuildMentions();
    toast.show('People mentioned rebuilt from transcripts');
  };

  const handleSuggestTask = async (event: TimelineEvent) => {
    try {
      await suggestTaskFromEvent(event.event_id);
      toast.show('Task suggested - view it in the Action Center', 'success');
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Could not suggest a task for this event', 'error');
    }
  };

  if (notFound) {
    return (
      <div className="content-max patient-profile-page">
        <EmptyState icon={<ShieldQuestion size={22} />} title="Patient not found" description="This patient ID does not exist." />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="content-max patient-profile-page">
        <Skeleton variant="card" count={1} />
        <div className="patient-timeline-list"><Skeleton variant="card" count={4} /></div>
      </div>
    );
  }

  if (error) {
    return <div className="content-max patient-profile-page"><ErrorState message={error} /></div>;
  }

  return (
    <div className="content-max patient-profile-page">
      <Card padding="md" className="patient-summary-header">
        <div className="patient-summary-top">
          <div>
            <h2>{patient?.name}</h2>
            <span className="patient-summary-meta">{patient?.id} · age {patient?.age}</span>
          </div>
          <Button variant="secondary" size="sm" loading={rebuilding} onClick={handleRebuild} leftIcon={<RotateCcw size={14} />}>
            Rebuild timeline
          </Button>
        </div>
        <div className="patient-summary-stats">
          <Badge tone="outline">{events.length} timeline event{events.length === 1 ? '' : 's'}</Badge>
          <Badge tone={unreviewedCount > 0 ? 'warning' : 'success'}>{unreviewedCount} unreviewed</Badge>
        </div>
        <p className="patient-summary-disclaimer">
          Observed transcript events - not diagnosis. Every event links to the exact call and turns it came from.
        </p>
      </Card>

      <Card padding="sm" className="patient-timeline-filter-row">
        <Select
          aria-label="Filter by event type"
          placeholder="All event types"
          options={Object.keys(TIMELINE_EVENT_TYPE_META).map((type) => ({ value: type, label: timelineEventTypeMeta(type).label }))}
          value={eventTypeFilter}
          onChange={(event) => setEventTypeFilter(event.target.value)}
        />
        <Select
          aria-label="Filter by review status"
          placeholder="All review statuses"
          options={REVIEW_STATUSES.map((status) => ({ value: status, label: reviewStatusLabel(status) }))}
          value={reviewStatusFilter}
          onChange={(event) => setReviewStatusFilter(event.target.value)}
        />
        {(eventTypeFilter || reviewStatusFilter) ? (
          <Button variant="ghost" size="sm" onClick={() => { setEventTypeFilter(''); setReviewStatusFilter(''); }}>
            Clear all
          </Button>
        ) : null}
      </Card>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Clock size={22} />}
          title={events.length === 0 ? 'No timeline events yet' : 'No events match your filters'}
          description={events.length === 0 ? 'Rebuild the timeline once calls have been ingested for this patient.' : 'Try clearing the filters above.'}
        />
      ) : (
        <ol className="patient-timeline-list">
          {filtered.map((event) => {
            const meta = timelineEventTypeMeta(event.event_type);
            const Icon = meta.icon;
            return (
              <li key={event.event_id} className="card card-pad-md patient-timeline-card">
                <div className="patient-timeline-top">
                  <span className="patient-timeline-icon" style={{ background: meta.bg, color: meta.fg }} aria-hidden="true">
                    <Icon size={16} />
                  </span>
                  <div className="patient-timeline-identity">
                    <strong>{event.title}</strong>
                    <span className="patient-timeline-meta">
                      {event.observed_date} · {event.source_call_id} · turn {event.source_turn_start}
                      {event.source_turn_end !== event.source_turn_start ? `-${event.source_turn_end}` : ''}
                    </span>
                  </div>
                  <Badge tone={event.review_status === 'unreviewed' ? 'warning' : event.review_status === 'dismissed' ? 'neutral' : 'success'}>
                    {reviewStatusLabel(event.review_status)}
                  </Badge>
                </div>
                <p className="patient-timeline-description">{event.description}</p>
                <blockquote className="patient-timeline-quote">&ldquo;{event.quote}&rdquo;</blockquote>
                <div className="patient-timeline-actions">
                  <button
                    type="button"
                    className="source-action patient-timeline-evidence-btn"
                    onClick={() => openTranscript({
                      callId: event.source_call_id,
                      turnStart: event.source_turn_start,
                      turnEnd: event.source_turn_end,
                      focusTurn: event.source_turn_start,
                    })}
                  >
                    Open transcript evidence <ArrowUpRight size={13} aria-hidden="true" />
                  </button>
                  <div className="patient-timeline-review-actions">
                    <Button
                      variant="ghost" size="sm" leftIcon={<ClipboardPlus size={13} />}
                      onClick={() => handleSuggestTask(event)}
                      disabled={!hasPermission('manage_tasks')}
                      title={!hasPermission('manage_tasks') ? "Your current role can't create tasks." : undefined}
                    >
                      Suggest task
                    </Button>
                    <Button
                      variant="ghost" size="sm" leftIcon={<CheckCircle2 size={13} />}
                      onClick={() => handleReview(event, 'confirmed')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Confirm
                    </Button>
                    <Button
                      variant="ghost" size="sm" leftIcon={<RotateCcw size={13} />}
                      onClick={() => handleReview(event, 'corrected')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Mark corrected
                    </Button>
                    <Button
                      variant="ghost" size="sm" leftIcon={<XCircle size={13} />}
                      onClick={() => handleReview(event, 'dismissed')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      <section className="patient-patterns-section">
        <div className="patient-patterns-header">
          <h3><TrendingUp size={16} aria-hidden="true" /> Observed patterns</h3>
          <Button
            variant="secondary" size="sm" loading={patternsRebuilding}
            onClick={handleRebuildPatterns} leftIcon={<RotateCcw size={14} />}
          >
            Rebuild patterns
          </Button>
        </div>
        <p className="patient-summary-disclaimer">
          Pattern detected from transcript history - not a clinical conclusion. Every pattern links back to the
          exact timeline events and calls it was derived from.
        </p>

        {patternsLoading ? (
          <Skeleton variant="card" count={2} />
        ) : patternsError ? (
          <ErrorState message={patternsError} />
        ) : patterns.length === 0 ? (
          <EmptyState
            icon={<TrendingUp size={22} />}
            title="No patterns detected yet"
            description="Patterns are derived from timeline events - rebuild after the timeline has events."
          />
        ) : (
          <ol className="patient-timeline-list">
            {patterns.map((pattern) => (
              <li key={pattern.pattern_id} className="card card-pad-md patient-timeline-card">
                <div className="patient-timeline-top">
                  <div className="patient-timeline-identity">
                    <strong>{pattern.title}</strong>
                    <span className="patient-timeline-meta">
                      {patternTypeLabel(pattern.pattern_type)} · {pattern.first_observed_date} to{' '}
                      {pattern.latest_observed_date}
                    </span>
                  </div>
                  <Badge tone={patternSeverityBadgeTone(pattern.severity)}>{patternSeverityLabel(pattern.severity)}</Badge>
                  <Badge tone="outline">{patternStatusLabel(pattern.status)}</Badge>
                </div>
                <p className="patient-timeline-description">{pattern.summary}</p>
                <div className="pattern-evidence-trail">
                  {pattern.evidence.map((ref, index) => (
                    <button
                      key={`${ref.timeline_event_id}-${index}`}
                      type="button"
                      className="source-action patient-timeline-evidence-btn pattern-evidence-item"
                      onClick={() => openTranscript({
                        callId: ref.call_id, turnStart: ref.turn_start, turnEnd: ref.turn_end, focusTurn: ref.turn_start,
                      })}
                    >
                      Open {ref.call_id} (turn {ref.turn_start}) <ArrowUpRight size={12} aria-hidden="true" />
                    </button>
                  ))}
                </div>
                <div className="patient-timeline-actions">
                  <Badge tone={pattern.reviewed_status === 'unreviewed' ? 'warning' : 'success'}>
                    {patternReviewedStatusLabel(pattern.reviewed_status)}
                  </Badge>
                  <div className="patient-timeline-review-actions">
                    <Button
                      variant="ghost" size="sm" leftIcon={<CheckCircle2 size={13} />}
                      onClick={() => handlePatternReview(pattern, 'confirmed')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Confirm
                    </Button>
                    <Button
                      variant="ghost" size="sm" leftIcon={<RotateCcw size={13} />}
                      onClick={() => handlePatternReview(pattern, 'corrected')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Mark corrected
                    </Button>
                    <Button
                      variant="ghost" size="sm" leftIcon={<XCircle size={13} />}
                      onClick={() => handlePatternReview(pattern, 'dismissed')}
                      disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="patient-patterns-section">
        <div className="patient-patterns-header">
          <h3><Users size={16} aria-hidden="true" /> People mentioned</h3>
          <Button
            variant="secondary" size="sm" loading={mentionsRebuilding}
            onClick={handleRebuildMentions} leftIcon={<RotateCcw size={14} />}
          >
            Rebuild
          </Button>
        </div>
        <p className="patient-summary-disclaimer">
          People other than the patient referenced in the transcripts - not a verified relationship record.
          "Unclear - needs review" means the transcript didn't unambiguously say whose relation this is.
        </p>

        {mentionsLoading ? (
          <Skeleton variant="card" count={2} />
        ) : mentionsError ? (
          <ErrorState message={mentionsError} />
        ) : mentions.length === 0 ? (
          <EmptyState
            icon={<Users size={22} />}
            title="No people mentioned yet"
            description="People mentioned are derived from call transcripts - rebuild once calls have been ingested."
          />
        ) : (
          <ol className="patient-timeline-list">
            {mentions.map((mention) => {
              const draft = correctionDrafts[mention.mention_id] ?? { relationshipType: '', name: mention.mentioned_name ?? '' };
              return (
                <li key={mention.mention_id} className="card card-pad-md patient-timeline-card">
                  <div className="patient-timeline-top">
                    <div className="patient-timeline-identity">
                      <strong>{mention.mentioned_name ?? relationshipTypeLabel(mention.role_label)}</strong>
                      <span className="patient-timeline-meta">
                        {mention.role_label} · {mention.source_call_id} · turn {mention.source_turn}
                      </span>
                    </div>
                    <Badge tone={relationshipTypeBadgeTone(mention.relationship_type)}>
                      {relationshipTypeLabel(mention.relationship_type)}
                    </Badge>
                    <Badge tone={mention.review_status === 'unreviewed' ? 'warning' : 'success'}>
                      {personMentionReviewStatusLabel(mention.review_status)}
                    </Badge>
                  </div>
                  <blockquote className="patient-timeline-quote">&ldquo;{mention.quote}&rdquo;</blockquote>
                  <div className="patient-timeline-actions">
                    <button
                      type="button"
                      className="source-action patient-timeline-evidence-btn"
                      onClick={() => openTranscript({
                        callId: mention.source_call_id,
                        turnStart: mention.source_turn,
                        turnEnd: mention.source_turn,
                        focusTurn: mention.source_turn,
                      })}
                    >
                      Open transcript evidence <ArrowUpRight size={13} aria-hidden="true" />
                    </button>
                    <div className="patient-timeline-review-actions">
                      <Button
                        variant="ghost" size="sm" leftIcon={<CheckCircle2 size={13} />}
                        onClick={() => handleMentionReview(mention, 'confirmed')}
                        disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                      >
                        Confirm
                      </Button>
                      <Button
                        variant="ghost" size="sm" leftIcon={<XCircle size={13} />}
                        onClick={() => handleMentionReview(mention, 'dismissed')}
                        disabled={!canReview} title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                  {mention.relationship_type === 'unknown' ? (
                    <div className="person-mention-correction-row">
                      <Select
                        aria-label={`Correct relationship for ${mention.mention_id}`}
                        placeholder="Who is this?"
                        options={CORRECTABLE_RELATIONSHIP_TYPES.map((type) => ({ value: type, label: relationshipTypeLabel(type) }))}
                        value={draft.relationshipType}
                        onChange={(e) => setCorrectionDrafts((current) => ({
                          ...current, [mention.mention_id]: { ...draft, relationshipType: e.target.value },
                        }))}
                      />
                      <Input
                        aria-label={`Name for ${mention.mention_id}`}
                        placeholder="Name (optional)"
                        value={draft.name}
                        onChange={(e) => setCorrectionDrafts((current) => ({
                          ...current, [mention.mention_id]: { ...draft, name: e.target.value },
                        }))}
                      />
                      <Button
                        size="sm" onClick={() => handleSaveCorrection(mention)}
                        disabled={!draft.relationshipType || !canReview}
                        title={!canReview ? REVIEW_DISABLED_TITLE : undefined}
                      >
                        Save correction
                      </Button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}
