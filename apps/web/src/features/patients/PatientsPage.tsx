import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Search, User, Users } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { usePatientsWithTimelineSummary } from './usePatientsWithTimelineSummary';
import './patients.css';

export function PatientsPage() {
  const { patients, loading, error } = usePatientsWithTimelineSummary();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return patients;
    return patients.filter((p) => `${p.name} ${p.id}`.toLowerCase().includes(query));
  }, [patients, search]);

  return (
    <div className="content-max patients-page">
      <Card padding="md" className="patients-filter-card">
        <Input
          icon={<Search size={15} />}
          placeholder="Search by patient name or ID"
          aria-label="Search patients"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <p className="field-hint">{patients.length} patients. Each profile shows an observed-events timeline - not a diagnosis.</p>
      </Card>

      {loading ? (
        <div className="patients-grid"><Skeleton variant="card" count={6} /></div>
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Users size={22} />}
          title={patients.length === 0 ? 'No patients yet' : 'No patients match your search'}
          description={patients.length === 0 ? 'Ingest calls to populate the patient roster.' : 'Try a different name or ID.'}
        />
      ) : (
        <div className="patients-grid">
          {filtered.map((patient) => (
            <button
              key={patient.id}
              type="button"
              className="card card-pad-md card-interactive patient-card"
              onClick={() => navigate(`/patients/${encodeURIComponent(patient.id)}`)}
            >
              <div className="patient-card-top">
                <span className="patient-card-icon" aria-hidden="true"><User size={16} /></span>
                <div className="patient-card-identity">
                  <strong>{patient.name}</strong>
                  <span className="patient-card-meta">{patient.id} · age {patient.age}</span>
                </div>
                <ArrowUpRight size={15} aria-hidden="true" />
              </div>
              <div className="patient-card-bottom">
                <Badge tone="outline">{patient.timeline_event_count} timeline event{patient.timeline_event_count === 1 ? '' : 's'}</Badge>
                {patient.unreviewed_event_count > 0 ? (
                  <Badge tone="warning">{patient.unreviewed_event_count} unreviewed</Badge>
                ) : (
                  <Badge tone="success">All reviewed</Badge>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
