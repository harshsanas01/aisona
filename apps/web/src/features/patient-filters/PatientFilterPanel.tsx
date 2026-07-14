import { useId, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { usePatients } from './usePatients';
import type { Filters } from '../../hooks/useAskQuestion';
import { Select } from '../../components/ui/Select';
import { DateInput } from '../../components/ui/DateInput';
import { FilterChip } from '../../components/ui/FilterChip';
import { Button } from '../../components/ui/Button';

interface PatientFilterPanelProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function PatientFilterPanel({ filters, onChange }: PatientFilterPanelProps) {
  const patients = usePatients();
  const panelId = useId();
  const [expanded, setExpanded] = useState(false);
  const activeCount = [filters.patientId, filters.startDate, filters.endDate].filter(Boolean).length;
  const hasActiveFilters = activeCount > 0;

  const patientName = filters.patientId
    ? patients.find((p) => p.id === filters.patientId)?.name ?? filters.patientId
    : null;

  const clearAll = () => onChange({ patientId: null, startDate: null, endDate: null });

  return (
    <div className="ask-filter-bar">
      <div className="ask-filter-toggle-row">
        <button
          type="button"
          className="filter-chip"
          aria-expanded={expanded}
          aria-controls={panelId}
          onClick={() => setExpanded((prev) => !prev)}
        >
          <SlidersHorizontal size={13} aria-hidden="true" />
          Filters {hasActiveFilters ? `(${activeCount})` : ''}
        </button>

        {patientName ? (
          <FilterChip active onRemove={() => onChange({ ...filters, patientId: null })}>{patientName}</FilterChip>
        ) : null}
        {filters.startDate ? (
          <FilterChip active onRemove={() => onChange({ ...filters, startDate: null })}>From {filters.startDate}</FilterChip>
        ) : null}
        {filters.endDate ? (
          <FilterChip active onRemove={() => onChange({ ...filters, endDate: null })}>To {filters.endDate}</FilterChip>
        ) : null}
        {hasActiveFilters ? <Button variant="ghost" size="sm" onClick={clearAll}>Clear all</Button> : null}
      </div>

      {expanded ? (
        <div id={panelId} className="ask-filter-panel">
          <Select
            label="Patient"
            placeholder="All patients"
            options={patients.map((patient) => ({ value: patient.id, label: patient.name }))}
            value={filters.patientId ?? ''}
            onChange={(event) => onChange({ ...filters, patientId: event.target.value || null })}
          />
          <DateInput
            label="From"
            value={filters.startDate ?? ''}
            onChange={(event) => onChange({ ...filters, startDate: event.target.value || null })}
          />
          <DateInput
            label="To"
            value={filters.endDate ?? ''}
            onChange={(event) => onChange({ ...filters, endDate: event.target.value || null })}
          />
        </div>
      ) : null}
    </div>
  );
}
