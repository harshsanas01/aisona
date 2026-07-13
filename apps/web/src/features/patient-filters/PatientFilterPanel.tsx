import { usePatients } from './usePatients';
import type { Filters } from '../../hooks/useAskQuestion';

interface PatientFilterPanelProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function PatientFilterPanel({ filters, onChange }: PatientFilterPanelProps) {
  const patients = usePatients();
  const hasActiveFilters = Boolean(filters.patientId || filters.startDate || filters.endDate);

  const patientName = filters.patientId
    ? patients.find((p) => p.id === filters.patientId)?.name ?? filters.patientId
    : null;

  return (
    <div className="filter-panel">
      <div className="filter-row">
        <label className="field-label" htmlFor="patient-filter">Patient</label>
        <select
          id="patient-filter"
          value={filters.patientId ?? ''}
          onChange={(event) => onChange({ ...filters, patientId: event.target.value || null })}
        >
          <option value="">All patients</option>
          {patients.map((patient) => (
            <option key={patient.id} value={patient.id}>{patient.name}</option>
          ))}
        </select>
      </div>

      <div className="filter-row">
        <label className="field-label" htmlFor="start-date-filter">From</label>
        <input
          id="start-date-filter"
          type="date"
          value={filters.startDate ?? ''}
          onChange={(event) => onChange({ ...filters, startDate: event.target.value || null })}
        />
        <label className="field-label" htmlFor="end-date-filter">To</label>
        <input
          id="end-date-filter"
          type="date"
          value={filters.endDate ?? ''}
          onChange={(event) => onChange({ ...filters, endDate: event.target.value || null })}
        />
      </div>

      {hasActiveFilters ? (
        <div className="active-filters">
          <span>
            Filtering by{patientName ? ` ${patientName}` : ''}
            {filters.startDate ? ` from ${filters.startDate}` : ''}
            {filters.endDate ? ` to ${filters.endDate}` : ''}
          </span>
          <button
            type="button"
            className="secondary"
            onClick={() => onChange({ patientId: null, startDate: null, endDate: null })}
          >
            Clear filters
          </button>
        </div>
      ) : null}
    </div>
  );
}
