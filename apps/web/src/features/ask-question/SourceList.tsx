import type { Citation } from '../../types';
import { SourceCard } from '../../components/ui/SourceCard';

interface SourceListProps {
  citations: Citation[];
  onOpenCitation: (citation: Citation) => void;
}

export function SourceList({ citations, onOpenCitation }: SourceListProps) {
  if (!citations.length) return null;
  return (
    <div className="sources">
      <h3>Sources</h3>
      <div className="source-list">
        {citations.map((citation, index) => (
          <SourceCard key={`${citation.call_id}-${index}`} citation={citation} order={index + 1} onOpen={onOpenCitation} />
        ))}
      </div>
    </div>
  );
}
