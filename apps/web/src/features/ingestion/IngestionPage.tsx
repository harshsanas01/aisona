import { useRef, useState, type DragEvent } from 'react';
import { CheckCircle2, Copy, FileJson, Search, UploadCloud, XCircle } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Textarea } from '../../components/ui/Textarea';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { useToast } from '../../components/ui/Toast';
import { ingestCallsBatch, type IngestResult } from '../../services/api';
import { MAX_BATCH_SIZE, SAMPLE_PAYLOAD, validateIngestPayload } from './validateIngestPayload';
import './ingestion.css';

export function IngestionPage() {
  const [raw, setRaw] = useState('');
  const [clientErrors, setClientErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState<IngestResult[] | null>(null);
  const [submitError, setSubmitError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { show } = useToast();

  const loadFile = (file: File) => {
    file.text().then(setRaw).catch(() => show('Could not read that file as text', 'error'));
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) loadFile(file);
  };

  const handleSubmit = async () => {
    setResults(null);
    setSubmitError('');
    const { calls, errors } = validateIngestPayload(raw);
    setClientErrors(errors);
    if (errors.length > 0) return;

    setSubmitting(true);
    try {
      const response = await ingestCallsBatch(calls);
      setResults(response);
      const created = response.filter((r) => r.status === 'created').length;
      const duplicate = response.filter((r) => r.status === 'duplicate').length;
      if (created > 0) show(`${created} call${created === 1 ? '' : 's'} ingested and now searchable.`, 'success');
      else if (duplicate > 0) show('All calls were already ingested (idempotent, no changes made).', 'info');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Ingestion failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="content-max ingestion-page">
      <div className="ingestion-grid">
        <Card padding="md">
          <h2 className="ingestion-section-title">1. Provide call transcripts</h2>

          <div
            className={`ingestion-dropzone ${dragActive ? 'active' : ''}`}
            onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInputRef.current?.click(); }}
            aria-label="Upload a JSON file of call transcripts"
          >
            <UploadCloud size={20} aria-hidden="true" />
            <span>Drop a <code>.json</code> file here, or click to browse</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              className="visually-hidden"
              onChange={(event) => { const file = event.target.files?.[0]; if (file) loadFile(file); event.target.value = ''; }}
            />
          </div>

          <Textarea
            label="…or paste JSON directly"
            hint={`Accepts a JSON array of calls, or {"calls": [...]}. Max ${MAX_BATCH_SIZE} calls per batch.`}
            rows={14}
            value={raw}
            onChange={(event) => setRaw(event.target.value)}
            placeholder={SAMPLE_PAYLOAD}
            spellCheck={false}
          />

          <div className="ingestion-actions">
            <Button variant="secondary" size="sm" leftIcon={<Copy size={14} />} onClick={() => setRaw(SAMPLE_PAYLOAD)}>
              Load sample
            </Button>
            <Button onClick={handleSubmit} loading={submitting} leftIcon={<UploadCloud size={16} />}>
              Ingest calls
            </Button>
          </div>

          {clientErrors.length > 0 ? (
            <div className="ingestion-errors" role="alert">
              <strong>Fix these before submitting:</strong>
              <ul>{clientErrors.map((message) => <li key={message}>{message}</li>)}</ul>
            </div>
          ) : null}

          {submitError ? <div className="error" role="alert">{submitError}</div> : null}

          {results ? (
            <div className="ingestion-results">
              <h3>Result summary</h3>
              <ul className="ingestion-results-list">
                {results.map((result) => (
                  <li key={result.call_id} className="ingestion-result-row">
                    {result.status === 'created' ? (
                      <CheckCircle2 size={15} className="ingestion-icon-success" aria-hidden="true" />
                    ) : result.status === 'duplicate' ? (
                      <Copy size={15} className="ingestion-icon-neutral" aria-hidden="true" />
                    ) : (
                      <XCircle size={15} className="ingestion-icon-error" aria-hidden="true" />
                    )}
                    <span className="ingestion-result-id">{result.call_id}</span>
                    <Badge tone={result.status === 'created' ? 'success' : result.status === 'duplicate' ? 'neutral' : 'danger'}>
                      {result.status}
                    </Badge>
                    {result.status === 'created' ? <span className="ingestion-chunk-count">{result.chunk_count} chunks</span> : null}
                    {result.error ? <span className="ingestion-result-error">{result.error}</span> : null}
                  </li>
                ))}
              </ul>
              {results.some((r) => r.status === 'created') ? (
                <p className="ingestion-confirmation">
                  <Search size={13} aria-hidden="true" /> Newly ingested calls are immediately searchable from Ask and Calls.
                </p>
              ) : null}
            </div>
          ) : null}
        </Card>

        <Card padding="md">
          <h2 className="ingestion-section-title"><FileJson size={16} aria-hidden="true" /> Schema guidance</h2>
          <p className="field-hint">Each call in the batch needs this shape:</p>
          <pre className="ingestion-schema"><code>{`{
  "call_id": string,        // unique identifier, e.g. "call_101"
  "date": string,           // "YYYY-MM-DD"
  "patient": {
    "id": string,
    "name": string,
    "age": number            // 0-130
  },
  "duration_seconds": number, // >= 0
  "turns": [
    { "speaker": string, "text": string }  // at least 1 turn
  ]
}`}</code></pre>
          <ul className="ingestion-notes">
            <li>Batches accept 1-{MAX_BATCH_SIZE} calls per request (<code>POST /api/calls/batch</code>).</li>
            <li>Re-ingesting the same <code>call_id</code> is idempotent - it comes back as <Badge tone="neutral">duplicate</Badge>, not an error.</li>
            <li>Validation runs client-side first, then again on the server; server errors are shown verbatim.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
