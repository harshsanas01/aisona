import { useEffect, useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { DateInput } from '../../components/ui/DateInput';
import { Button } from '../../components/ui/Button';
import { createTask } from '../../services/api';
import type { Patient } from '../../types';
import { LOCAL_ASSIGNEE_SUGGESTIONS, TASK_CATEGORIES, TASK_PRIORITIES, taskCategoryLabel, taskPriorityLabel } from './taskMeta';

export interface TaskSourceEvidence {
  patientId: string;
  title?: string;
  description?: string;
  callId?: string;
  turnStart?: number;
  turnEnd?: number;
  eventId?: string;
}

interface CreateTaskModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  patients: Patient[];
  /** Pre-fills the form when creating a task directly from a citation or timeline event. */
  sourceEvidence?: TaskSourceEvidence | null;
}

export function CreateTaskModal({ open, onClose, onCreated, patients, sourceEvidence }: CreateTaskModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [patientId, setPatientId] = useState('');
  const [category, setCategory] = useState('general_outreach');
  const [priority, setPriority] = useState('normal');
  const [assignee, setAssignee] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setTitle(sourceEvidence?.title ?? '');
    setDescription(sourceEvidence?.description ?? '');
    setPatientId(sourceEvidence?.patientId ?? '');
    setCategory('general_outreach');
    setPriority('normal');
    setAssignee('');
    setDueDate('');
    setError('');
  }, [open, sourceEvidence]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim() || !description.trim() || !patientId) {
      setError('Title, description, and patient are required.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await createTask({
        title: title.trim(),
        description: description.trim(),
        patient_id: patientId,
        category,
        priority,
        assignee: assignee.trim() || null,
        due_date: dueDate || null,
        source_event_id: sourceEvidence?.eventId ?? null,
        source_call_id: sourceEvidence?.callId ?? null,
        source_turn_start: sourceEvidence?.turnStart ?? null,
        source_turn_end: sourceEvidence?.turnEnd ?? null,
      });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create follow-up task">
      <form onSubmit={handleSubmit} className="create-task-form">
        {sourceEvidence?.callId ? (
          <div className="create-task-evidence-preview">
            Linked evidence: call {sourceEvidence.callId}
            {sourceEvidence.turnStart ? `, turn ${sourceEvidence.turnStart}` : ''}
          </div>
        ) : null}
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          hint="No medical advice - describe the follow-up action only."
          required
        />
        <Select
          label="Patient"
          placeholder="Select a patient"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          options={patients.map((p) => ({ value: p.id, label: p.name }))}
          disabled={Boolean(sourceEvidence?.patientId)}
        />
        <div className="create-task-row">
          <Select
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            options={TASK_CATEGORIES.map((c) => ({ value: c, label: taskCategoryLabel(c) }))}
          />
          <Select
            label="Priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            options={TASK_PRIORITIES.map((p) => ({ value: p, label: taskPriorityLabel(p) }))}
          />
        </div>
        <div className="create-task-row">
          <Input
            label="Assignee (optional)"
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            placeholder="e.g. Nurse Amy"
            list="assignee-suggestions"
          />
          <datalist id="assignee-suggestions">
            {LOCAL_ASSIGNEE_SUGGESTIONS.map((name) => <option key={name} value={name} />)}
          </datalist>
          <DateInput label="Due date (optional)" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </div>
        {error ? <p className="field-error">{error}</p> : null}
        <div className="create-task-actions">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={submitting}>Create task</Button>
        </div>
      </form>
    </Modal>
  );
}
