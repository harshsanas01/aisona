import { useMemo, useState } from 'react';
import { AlertTriangle, LayoutGrid, List as ListIcon, Plus } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Select } from '../../components/ui/Select';
import { Input } from '../../components/ui/Input';
import { EmptyState } from '../../components/ui/EmptyState';
import { ErrorState } from '../../components/ui/ErrorState';
import { Skeleton } from '../../components/ui/Skeleton';
import { usePatients } from '../patient-filters/usePatients';
import { useTasks } from './useTasks';
import { CreateTaskModal } from './CreateTaskModal';
import { TaskDetailsDrawer } from './TaskDetailsDrawer';
import {
  TASK_CATEGORIES, TASK_PRIORITIES, TASK_STATUSES, isTaskOverdue,
  taskCategoryLabel, taskPriorityBadgeTone, taskPriorityLabel, taskStatusBadgeTone, taskStatusLabel,
} from './taskMeta';
import type { CoordinatorTask } from '../../types';
import './tasks.css';

const BOARD_COLUMNS = ['open', 'in_progress', 'blocked', 'completed', 'dismissed'] as const;

export function ActionCenterPage() {
  const patients = usePatients();
  const [view, setView] = useState<'list' | 'board'>('list');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [patientFilter, setPatientFilter] = useState('');
  const [assigneeFilter, setAssigneeFilter] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const { tasks, loading, error, refresh } = useTasks({
    patientId: patientFilter || null,
    status: view === 'list' ? (statusFilter || null) : null,
    priority: priorityFilter || null,
    category: categoryFilter || null,
    assignee: assigneeFilter || null,
  });

  const filtered = useMemo(() => (overdueOnly ? tasks.filter(isTaskOverdue) : tasks), [tasks, overdueOnly]);
  const hasActiveFilters = Boolean(statusFilter || priorityFilter || categoryFilter || patientFilter || assigneeFilter || overdueOnly);

  const clearAll = () => {
    setStatusFilter(''); setPriorityFilter(''); setCategoryFilter('');
    setPatientFilter(''); setAssigneeFilter(''); setOverdueOnly(false);
  };

  const renderTaskCard = (task: CoordinatorTask) => {
    const overdue = isTaskOverdue(task);
    const patientName = patients.find((p) => p.id === task.patient_id)?.name ?? task.patient_id;
    return (
      <button
        key={task.task_id}
        type="button"
        className="card card-pad-md card-interactive task-card"
        onClick={() => setSelectedTaskId(task.task_id)}
      >
        <div className="task-card-top">
          <strong>{task.title}</strong>
          {task.is_suggested ? <Badge tone="violet">Suggested</Badge> : null}
        </div>
        <span className="task-card-meta">{patientName} &middot; {taskCategoryLabel(task.category)}</span>
        <div className="task-card-badges">
          <Badge tone={taskStatusBadgeTone(task.status)}>{taskStatusLabel(task.status)}</Badge>
          <Badge tone={taskPriorityBadgeTone(task.priority)}>{taskPriorityLabel(task.priority)}</Badge>
          {overdue ? <Badge tone="danger" icon={<AlertTriangle size={12} />}>Overdue</Badge> : null}
          {task.assignee ? <Badge tone="outline">{task.assignee}</Badge> : null}
          {task.due_date ? <Badge tone="neutral">Due {task.due_date}</Badge> : null}
        </div>
      </button>
    );
  };

  return (
    <div className="content-max action-center-page">
      <Card padding="md" className="action-center-filter-card">
        <div className="action-center-filter-row">
          <Select
            aria-label="Filter by patient"
            placeholder="All patients"
            options={patients.map((p) => ({ value: p.id, label: p.name }))}
            value={patientFilter}
            onChange={(e) => setPatientFilter(e.target.value)}
          />
          {view === 'list' ? (
            <Select
              aria-label="Filter by status"
              placeholder="All statuses"
              options={TASK_STATUSES.map((s) => ({ value: s, label: taskStatusLabel(s) }))}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            />
          ) : null}
          <Select
            aria-label="Filter by priority"
            placeholder="All priorities"
            options={TASK_PRIORITIES.map((p) => ({ value: p, label: taskPriorityLabel(p) }))}
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          />
          <Select
            aria-label="Filter by category"
            placeholder="All categories"
            options={TASK_CATEGORIES.map((c) => ({ value: c, label: taskCategoryLabel(c) }))}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          />
          <Input
            aria-label="Filter by assignee"
            placeholder="Assignee"
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
          />
          <button
            type="button"
            className={`filter-chip ${overdueOnly ? 'active' : ''}`}
            onClick={() => setOverdueOnly((v) => !v)}
          >
            Overdue only
          </button>
          {hasActiveFilters ? <Button variant="ghost" size="sm" onClick={clearAll}>Clear all</Button> : null}
        </div>

        <div className="action-center-toolbar">
          <div className="action-center-view-toggle" role="group" aria-label="View mode">
            <button type="button" className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>
              <ListIcon size={14} aria-hidden="true" /> List
            </button>
            <button type="button" className={view === 'board' ? 'active' : ''} onClick={() => setView('board')}>
              <LayoutGrid size={14} aria-hidden="true" /> Board
            </button>
          </div>
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>New task</Button>
        </div>
      </Card>

      {loading ? (
        <Skeleton variant="card" count={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<ListIcon size={22} />}
          title="No tasks match"
          description="Create a task manually, or suggest one from a patient's timeline event."
        />
      ) : view === 'list' ? (
        <div className="task-list">{filtered.map(renderTaskCard)}</div>
      ) : (
        <div className="task-board">
          {BOARD_COLUMNS.map((status) => {
            const columnTasks = filtered.filter((t) => t.status === status);
            return (
              <div key={status} className="task-board-column">
                <div className="task-board-column-header">
                  <Badge tone={taskStatusBadgeTone(status)}>{taskStatusLabel(status)}</Badge>
                  <span className="task-board-count">{columnTasks.length}</span>
                </div>
                <div className="task-board-column-body">
                  {columnTasks.map(renderTaskCard)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <CreateTaskModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={refresh}
        patients={patients}
      />
      <TaskDetailsDrawer
        taskId={selectedTaskId}
        onClose={() => setSelectedTaskId(null)}
        onChanged={refresh}
      />
    </div>
  );
}
