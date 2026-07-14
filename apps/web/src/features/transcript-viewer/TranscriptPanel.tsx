import type { Citation, SafetyEvent, TranscriptCall } from '../../types';
import { safetyCategoryMeta } from '../safety/safetyCategories';

interface TranscriptPanelProps {
  transcript: TranscriptCall | null;
  activeCitation: Citation | null;
  safetyEvents: SafetyEvent[];
  activeSafetyCategory: string | null;
  onClose: () => void;
}

export function TranscriptPanel({
  transcript,
  activeCitation,
  safetyEvents,
  activeSafetyCategory,
  onClose,
}: TranscriptPanelProps) {
  if (!transcript) {
    return (
      <div className="empty-state">
        <h3>Transcript view</h3>
        <p>Select a source card to open the complete transcript and inspect the highlighted turns.</p>
      </div>
    );
  }

  const eventsByTurn = new Map<number, SafetyEvent[]>();
  for (const event of safetyEvents) {
    if (activeSafetyCategory && event.category !== activeSafetyCategory) continue;
    const list = eventsByTurn.get(event.turn_number) ?? [];
    list.push(event);
    eventsByTurn.set(event.turn_number, list);
  }

  return (
    <>
      <div className="transcript-header">
        <div>
          <h3>{transcript.patient.name}</h3>
          <p>{transcript.call_id} · {transcript.date}</p>
        </div>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
      <div className="turn-list">
        {transcript.turns.map((turn) => {
          const isCitationHighlighted = activeCitation
            ? turn.turn_number >= activeCitation.turn_start && turn.turn_number <= activeCitation.turn_end
            : false;
          const turnSafetyEvents = eventsByTurn.get(turn.turn_number) ?? [];
          return (
            <div
              key={turn.turn_number}
              className={`turn ${isCitationHighlighted ? 'highlighted' : ''} ${turnSafetyEvents.length ? 'safety-flagged' : ''}`}
            >
              <div className="turn-badge">{turn.turn_number}</div>
              <div>
                <strong>{turn.speaker}</strong>
                <p>{turn.text}</p>
                {turnSafetyEvents.length ? (
                  <div className="safety-badges">
                    {turnSafetyEvents.map((event, index) => {
                      const meta = safetyCategoryMeta(event.category);
                      return (
                        <span
                          key={`${event.category}-${index}`}
                          className="safety-badge"
                          style={{ background: meta.dot }}
                          title={event.explanation}
                        >
                          {meta.label} · {event.severity}
                        </span>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
