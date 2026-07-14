import { useMemo, useState } from 'react';
import { Search, Phone, Calendar, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { DateInput } from '../../components/ui/DateInput';
import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { Button } from '../../components/ui/Button';
import { useCalls } from './useCalls';
import { usePatients } from '../patient-filters/usePatients';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import './calls.css';

export function CallsPage() {
  const { calls, safetyCountByCall, loading, error } = useCalls();
  const patients = usePatients();
  const { open: openTranscript } = useTranscriptDrawer();

  const [search, setSearch] = useState('');
  const [patientId, setPatientId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return calls.filter((call) => {
      if (query) {
        const haystack = `${call.patient_name} ${call.call_id} ${call.date}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      if (patientId && !call.patient_name.toLowerCase().includes(
        (patients.find((p) => p.id === patientId)?.name ?? '').toLowerCase(),
      )) return false;
      if (startDate && call.date < startDate) return false;
      if (endDate && call.date > endDate) return false;
      return true;
    });
  }, [calls, search, patientId, startDate, endDate, patients]);

  const hasActiveFilters = Boolean(search || patientId || startDate || endDate);
  const clearAll = () => { setSearch(''); setPatientId(''); setStartDate(''); setEndDate(''); };

  return (
    <div className="content-max calls-page">
      <Card padding="md" className="calls-filter-card">
        <div className="calls-filter-row">
          <Input
            icon={<Search size={15} />}
            placeholder="Search by patient, call ID, or date"
            aria-label="Search calls"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Select
            aria-label="Filter by patient"
            placeholder="All patients"
            options={patients.map((patient) => ({ value: patient.id, label: patient.name }))}
            value={patientId}
            onChange={(event) => setPatientId(event.target.value)}
          />
          <DateInput aria-label="From date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          <DateInput aria-label="To date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          {hasActiveFilters ? <Button variant="ghost" size="sm" onClick={clearAll}>Clear all</Button> : null}
        </div>
        <p className="field-hint">Search matches patient name, call ID, and date. {calls.length} calls total.</p>
      </Card>

      {loading ? (
        <div className="calls-grid"><Skeleton variant="card" count={6} /></div>
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Phone size={22} />}
          title={calls.length === 0 ? 'No calls ingested yet' : 'No calls match your filters'}
          description={calls.length === 0 ? 'Use the Ingestion page to load transcripts.' : 'Try widening your search or clearing filters.'}
        />
      ) : (
        <div className="calls-grid">
          {filtered.map((call) => {
            const safetyCount = safetyCountByCall.get(call.call_id) ?? 0;
            return (
              <button
                key={call.call_id}
                type="button"
                className="card card-pad-md card-interactive call-card"
                onClick={() => openTranscript({ callId: call.call_id })}
              >
                <div className="call-card-top">
                  <strong>{call.patient_name}</strong>
                  <ArrowUpRight size={15} aria-hidden="true" />
                </div>
                <div className="call-card-meta">
                  <span><Calendar size={12} aria-hidden="true" /> {call.date}</span>
                  <span className="call-card-id"><Phone size={12} aria-hidden="true" /> {call.call_id}</span>
                </div>
                {safetyCount > 0 ? (
                  <Badge tone="warning" icon={<ShieldAlert size={12} />}>{safetyCount} safety flag{safetyCount === 1 ? '' : 's'}</Badge>
                ) : (
                  <Badge tone="neutral">No safety flags</Badge>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
