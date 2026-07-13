import type { Citation } from '../../types';

interface SourceListProps {
  citations: Citation[];
  onOpenCitation: (citation: Citation) => void;
}

export function SourceList({ citations, onOpenCitation }: SourceListProps) {
  if (!citations.length) return null;
  return (
    <div className="sources">
      <h3>Sources</h3>
      {citations.map((citation, index) => (
        <button
          key={`${citation.call_id}-${index}`}
          className="source-card"
          onClick={() => onOpenCitation(citation)}
        >
          <div className="source-topline">
            <strong>{citation.patient_name}</strong>
            <span>{citation.date}</span>
          </div>
          <div className="source-meta">{citation.call_id} · turns {citation.turn_start}-{citation.turn_end}</div>
          <p>{citation.quote}</p>
        </button>
      ))}
    </div>
  );
}
