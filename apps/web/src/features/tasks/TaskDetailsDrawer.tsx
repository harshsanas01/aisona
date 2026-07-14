import { useEffect, useState } from 'react';
import { ArrowUpRight, Clock } from 'lucide-react';
import { Drawer } from '../../components/ui/Drawer';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { DateInput } from '../../components/ui/DateInput';
import { Skeleton } from '../../components/ui/Skeleton';
import { useToast } from '../../components/ui/Toast';
import { getTask, updateTask } from '../../services/api';
import { useTranscriptDrawer } from '../transcript-viewer/TranscriptDrawerContext';
import type { CoordinatorTask, TaskActivityEntry } from '../../types';
import { isTaskOverdue, taskCategoryLabel, taskPriorityBadgeTone, taskPriorityLabel, taskStatusBadgeTone, taskStatusLabel } from './taskMeta';

const TASK_STATUS_TRANSITIONS: Record<string, string[]> = {
  open: ['in_progress', 'blocked', 'completed', 'dismissed'],
  in_progress: ['open', 'blocked', 'completed', 'dismissed'],
  blocked: ['open', 'in_progress', 'dismissed'],
  completed: ['open'],
  dismissed: ['open'],
};

interface TaskDetailsDrawerProps {
  taskId: string | null;
  onClose: () => void;
  onChanged: () => void;
}

export function TaskDetailsDrawer({ taskId, onClose, onChanged }: TaskDetailsDrawerProps) {
  const [task, setTask] = useState<CoordinatorTask | null>(null);
  const [activity, setActivity] = useState<TaskActivityEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigneeDraft, setAssigneeDraft] = useState('');
  const [dueDateDraft, setDueDateDraft] = useState('');
  const { open: openTranscript } = useTranscriptDrawer();
  const toast = useToast();

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    setLoading(true);
    getTask(taskId)
      .then((body: { task: CoordinatorTask; activity: TaskActivityEntry[] } | null) => {
        if (cancelled || !body) return;
        setTask(body.task);
        setActivity(body.activity);
        setAssigneeDraft(body.task.assignee ?? '');
        setDueDateDraft(body.task.due_date ?? '');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [taskId]);

  const refetch = async () => {
    if (!taskId) return;
    const body = await getTask(taskId);
    if (body) {
      setTask(body.task);
      setActivity(body.activity);
    }
    onChanged();
  };

  const handleStatusChange = async (status: string) => {
    if (!task) return;
    try {
      await updateTask(task.task_id, { status, actor: 'coordinator' });
      toast.show(`Marked as ${taskStatusLabel(status).toLowerCase()}`);
      await refetch();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update task', 'error');
    }
  };

  const handleAssigneeSave = async () => {
    if (!task) return;
    try {
      await updateTask(task.task_id, { assignee: assigneeDraft || null, actor: 'coordinator' });
      toast.show('Assignee updated');
      await refetch();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update assignee', 'error');
    }
  };

  const handleDueDateSave = async () => {
    if (!task) return;
    try {
      await updateTask(task.task_id, { due_date: dueDateDraft || null, actor: 'coordinator' });
      toast.show('Due date updated');
      await refetch();
    } catch (err) {
      toast.show(err instanceof Error ? err.message : 'Failed to update due date', 'error');
    }
  };

  return (
    <Drawer open={Boolean(taskId)} onClose={onClose} labelledBy="task-drawer-title">
      {loading || !task ? (
        <div style={{ padding: 'var(--space-5)' }}><Skeleton variant="card" count={3} /></div>
      ) : (
        <div className="task-drawer-content">
          <div className="task-drawer-header">
            <h2 id="task-drawer-title">{task.title}</h2>
            <div className="task-drawer-badges">
              <Badge tone={taskStatusBadgeTone(task.status)}>{taskStatusLabel(task.status)}</Badge>
              <Badge tone={taskPriorityBadgeTone(task.priority)}>{taskPriorityLabel(task.priority)}</Badge>
              {isTaskOverdue(task) ? <Badge tone="danger">Overdue</Badge> : null}
              {task.is_suggested ? <Badge tone="violet">Suggested</Badge> : null}
            </div>
          </div>

          <p className="task-drawer-description">{task.description}</p>
          <dl className="task-drawer-meta">
            <div><dt>Patient</dt><dd>{task.patient_id}</dd></div>
            <div><dt>Category</dt><dd>{taskCategoryLabel(task.category)}</dd></div>
            <div><dt>Created by</dt><dd>{task.created_by}</dd></div>
          </dl>

          {task.source_call_id ? (
            <button
              type="button"
              className="source-action patient-timeline-evidence-btn"
              onClick={() => openTranscript({
                callId: task.source_call_id!,
                turnStart: task.source_turn_start ?? undefined,
                turnEnd: task.source_turn_end ?? undefined,
                focusTurn: task.source_turn_start ?? undefined,
              })}
            >
              Open evidence: {task.source_call_id} <ArrowUpRight size={13} aria-hidden="true" />
            </button>
          ) : null}

          <div className="task-drawer-field-row">
            <Input label="Assignee" value={assigneeDraft} onChange={(e) => setAssigneeDraft(e.target.value)} onBlur={handleAssigneeSave} placeholder="Unassigned" />
            <DateInput label="Due date" value={dueDateDraft} onChange={(e) => setDueDateDraft(e.target.value)} onBlur={handleDueDateSave} />
          </div>

          <div className="task-drawer-status-actions">
            <span className="field-label">Change status</span>
            <div className="task-drawer-status-buttons">
              {(TASK_STATUS_TRANSITIONS[task.status] ?? []).map((status) => (
                <Button key={status} variant="secondary" size="sm" onClick={() => handleStatusChange(status)}>
                  {taskStatusLabel(status)}
                </Button>
              ))}
            </div>
          </div>

          <div className="task-drawer-activity">
            <h3><Clock size={14} aria-hidden="true" /> Activity history</h3>
            <ol className="task-activity-list">
              {activity.map((entry) => (
                <li key={entry.activity_id}>
                  <span className="task-activity-action">{entry.action.replace(/_/g, ' ')}</span>
                  {entry.from_status && entry.to_status ? (
                    <span className="task-activity-transition">{entry.from_status} &rarr; {entry.to_status}</span>
                  ) : entry.to_status ? (
                    <span className="task-activity-transition">&rarr; {entry.to_status}</span>
                  ) : null}
                  <span className="task-activity-meta">{entry.actor} &middot; {entry.created_at}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </Drawer>
  );
}
