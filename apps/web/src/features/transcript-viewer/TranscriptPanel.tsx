import type { Citation, TranscriptCall } from '../../types';

interface TranscriptPanelProps {
  transcript: TranscriptCall | null;
  activeCitation: Citation | null;
  onClose: () => void;
}

export function TranscriptPanel({ transcript, activeCitation, onClose }: TranscriptPanelProps) {
  if (!transcript) {
    return (
      <div className="empty-state">
        <h3>Transcript view</h3>
        <p>Select a source card to open the complete transcript and inspect the highlighted turns.</p>
      </div>
    );
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
          const isHighlighted = activeCitation
            ? turn.turn_number >= activeCitation.turn_start && turn.turn_number <= activeCitation.turn_end
            : false;
          return (
            <div key={turn.turn_number} className={`turn ${isHighlighted ? 'highlighted' : ''}`}>
              <div className="turn-badge">{turn.turn_number}</div>
              <div>
                <strong>{turn.speaker}</strong>
                <p>{turn.text}</p>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
