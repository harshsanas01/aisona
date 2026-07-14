import { useEffect, useState } from 'react';
import { FileText, Sparkles } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Select } from '../../components/ui/Select';
import { DateInput } from '../../components/ui/DateInput';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { usePatients } from '../patient-filters/usePatients';
import { useBriefGeneration } from './useBriefs';
import { BriefView } from './BriefView';
import { listBriefs } from '../../services/api';
import type { Brief } from '../../types';
import './briefs.css';

export function BriefsPage() {
  const patients = usePatients();
  const { brief, loading, error, generate, regenerate, load } = useBriefGeneration();

  const [type, setType] = useState<'daily' | 'weekly'>('weekly');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [patientId, setPatientId] = useState('');
  const [includeResolved, setIncludeResolved] = useState(false);

  const [pastBriefs, setPastBriefs] = useState<Brief[]>([]);
  const [pastLoading, setPastLoading] = useState(true);

  const refreshPastBriefs = () => {
    setPastLoading(true);
    listBriefs()
      .then((result: Brief[]) => setPastBriefs(result))
      .catch(() => setPastBriefs([]))
      .finally(() => setPastLoading(false));
  };

  useEffect(() => { refreshPastBriefs(); }, []);

  const handleGenerate = async () => {
    const result = await generate({
      type,
      start_date: startDate || null,
      end_date: endDate || null,
      patient_id: patientId || null,
      include_resolved: includeResolved,
    });
    if (result) refreshPastBriefs();
  };

  const handleRegenerate = async () => {
    if (!brief) return;
    await regenerate(brief.brief_id);
    refreshPastBriefs();
  };

  return (
    <div className="content-max briefs-page">
      <Card padding="md" className="briefs-generate-card no-print">
        <div className="briefs-generate-row">
          <Select
            label="Type"
            value={type}
            onChange={(e) => setType(e.target.value as 'daily' | 'weekly')}
            options={[{ value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }]}
          />
          <DateInput label="Start date (optional)" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <DateInput label="End date (optional)" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          <Select
            label="Patient"
            placeholder="Center-wide"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            options={patients.map((p) => ({ value: p.id, label: p.name }))}
          />
        </div>
        <label className="briefs-include-resolved">
          <input type="checkbox" checked={includeResolved} onChange={(e) => setIncludeResolved(e.target.checked)} />
          Include resolved items
        </label>
        <Button leftIcon={<Sparkles size={14} />} loading={loading} onClick={handleGenerate}>
          Generate brief
        </Button>
      </Card>

      {loading ? (
        <Skeleton variant="card" count={3} />
      ) : error ? (
        <ErrorState message={error} />
      ) : brief ? (
        <BriefView brief={brief} onRegenerate={handleRegenerate} regenerating={loading} />
      ) : (
        <EmptyState
          icon={<FileText size={22} />}
          title="No brief generated yet"
          description="Choose a type and date range above, then generate a brief."
        />
      )}

      <Card padding="md" className="briefs-history no-print">
        <h3>Previously generated briefs</h3>
        {pastLoading ? (
          <Skeleton variant="card" count={2} />
        ) : pastBriefs.length === 0 ? (
          <p className="field-hint">No briefs generated yet.</p>
        ) : (
          <ul className="briefs-history-list">
            {pastBriefs.map((b) => (
              <li key={b.brief_id}>
                <button type="button" className="briefs-history-item" onClick={() => load(b.brief_id)}>
                  {b.brief_type} &middot; {b.start_date} to {b.end_date} &middot; {b.patient_id ?? 'Center-wide'} &middot; {b.bullets.length} items
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
