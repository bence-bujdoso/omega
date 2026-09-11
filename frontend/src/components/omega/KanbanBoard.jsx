import { Loader2, CheckCircle2, XCircle, Circle, ScanSearch, FileCode2 } from "lucide-react";
import { TASK_STATUS, agentColor } from "./meta";

const COLUMNS = [
  { key: "TODO", label: "To Do" },
  { key: "IN_PROGRESS", label: "In Progress" },
  { key: "REVIEW", label: "Review" },
  { key: "DONE", label: "Done" },
  { key: "FAILED", label: "Failed" },
];

const STATUS_ICON = {
  TODO: Circle,
  IN_PROGRESS: Loader2,
  REVIEW: ScanSearch,
  DONE: CheckCircle2,
  FAILED: XCircle,
  BLOCKED: XCircle,
};

export default function KanbanBoard({ run }) {
  const tasks = run?.tasks || [];
  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      data-testid="kanban-task-board"
    >
      {COLUMNS.map((col) => {
        const items = tasks.filter((t) => (t.status || "TODO") === col.key);
        const meta = TASK_STATUS[col.key];
        return (
          <div
            key={col.key}
            className="rounded-xl border border-[#2A2E43] bg-[#0F111A] p-3 min-h-[160px]"
            data-testid={`kanban-col-${col.key}`}
          >
            <div className="flex items-center justify-between px-1 mb-3">
              <span className="text-xs font-mono uppercase tracking-wider" style={{ color: meta.color }}>
                {col.label}
              </span>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{ color: meta.color, background: meta.bg }}
              >
                {items.length}
              </span>
            </div>
            <div className="space-y-2.5">
              {items.map((t) => (
                <TaskCard key={t.id} task={t} />
              ))}
              {items.length === 0 && (
                <div className="text-[11px] font-mono text-slate-600 text-center py-4">empty</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TaskCard({ task }) {
  const meta = TASK_STATUS[task.status] || TASK_STATUS.TODO;
  const Icon = STATUS_ICON[task.status] || Circle;
  const spin = task.status === "IN_PROGRESS";
  return (
    <div
      className="rounded-lg border bg-[#12141D] p-3 hover:border-sky-500/50 transition-all duration-200 animate-fade-up"
      style={{ borderColor: `${meta.color}44` }}
      data-testid={`task-card-${task.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-[11px] text-slate-500">{task.id}</span>
        <Icon
          className={`w-4 h-4 shrink-0 ${spin ? "animate-spin" : ""}`}
          style={{ color: meta.color }}
        />
      </div>
      <p className="text-sm text-slate-200 font-medium mt-1 leading-snug">{task.title}</p>
      <div className="flex items-center gap-1.5 mt-2 text-[11px] font-mono text-slate-400">
        <FileCode2 className="w-3.5 h-3.5" />
        <span className="truncate">{task.filename}</span>
      </div>
      <div className="flex items-center flex-wrap gap-1.5 mt-2.5">
        <span
          className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded"
          style={{ color: agentColor(task.agent), background: `${agentColor(task.agent)}1f` }}
        >
          {task.agent}
        </span>
        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#1A1D2B] text-slate-400">
          {task.capability}
        </span>
        {task.iterations > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1A1D2B] text-slate-400">
            ×{task.iterations}
          </span>
        )}
      </div>
      {task.error && (
        <p className="text-[10px] font-mono text-rose-400/80 mt-2 line-clamp-2">{task.error}</p>
      )}
    </div>
  );
}
