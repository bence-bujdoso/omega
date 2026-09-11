import { Square, CheckCircle2, XCircle, Loader2, Repeat, Layers, Clock } from "lucide-react";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import { PHASES, STATUS_META, fmtDuration } from "./meta";

const ACTIVE = ["pending", "planning", "coding"];

export default function PipelineHeader({ run, onStop }) {
  if (!run) {
    return (
      <div className="flex items-center gap-3 text-slate-400" data-testid="pipeline-header-status">
        <Loader2 className="w-5 h-5 animate-spin text-sky-400" /> Initializing pipeline…
      </div>
    );
  }
  const meta = STATUS_META[run.status] || STATUS_META.pending;
  const pct = run.total_tasks ? Math.round((run.completed_tasks / run.total_tasks) * 100) : 0;
  const isActive = ACTIVE.includes(run.status);
  const phaseIdx = PHASES.findIndex((p) => p.key === (run.phase === "init" ? "architecture" : run.phase));

  return (
    <div
      className="rounded-xl border border-[#2A2E43] bg-[#12141D] p-5 sm:p-6 space-y-5"
      data-testid="pipeline-header-status"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="font-heading text-2xl font-bold tracking-tight" data-testid="run-project-name">
              {run.project_name}
            </h2>
            <span
              className="text-xs font-mono uppercase tracking-wider px-2.5 py-1 rounded-full flex items-center gap-1.5"
              style={{ color: meta.color, background: meta.bg }}
              data-testid="run-status-badge"
            >
              {run.status === "done" && <CheckCircle2 className="w-3.5 h-3.5" />}
              {run.status === "failed" && <XCircle className="w-3.5 h-3.5" />}
              {isActive && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {meta.label}
            </span>
          </div>
          <p className="text-[12px] font-mono text-slate-500 mt-1">run · {run.id?.slice(0, 8)}</p>
        </div>

        {isActive && (
          <Button
            onClick={onStop}
            variant="outline"
            className="border-rose-500/40 text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 gap-2"
            data-testid="stop-run-btn"
          >
            <Square className="w-4 h-4" /> Stop
          </Button>
        )}
      </div>

      {/* phase stepper */}
      <div className="flex items-center gap-1 sm:gap-2" data-testid="phase-stepper">
        {PHASES.map((p, i) => {
          const done = i < phaseIdx || run.status === "done";
          const current = i === phaseIdx && isActive;
          return (
            <div key={p.key} className="flex items-center gap-1 sm:gap-2 flex-1">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`w-6 h-6 rounded-full grid place-items-center text-[11px] font-mono font-semibold shrink-0 ${
                    done
                      ? "bg-emerald-500/20 text-emerald-400"
                      : current
                      ? "bg-sky-500/20 text-sky-400"
                      : "bg-[#1A1D2B] text-slate-500"
                  }`}
                >
                  {done ? "✓" : i + 1}
                </span>
                <span
                  className={`text-xs font-medium truncate hidden sm:inline ${
                    current ? "text-sky-400" : done ? "text-slate-300" : "text-slate-500"
                  }`}
                >
                  {p.label}
                </span>
              </div>
              {i < PHASES.length - 1 && (
                <div className={`h-px flex-1 ${done ? "bg-emerald-500/40" : "bg-[#2A2E43]"}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* progress + stats */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span>Task progress</span>
          <span data-testid="progress-label">
            {run.completed_tasks}/{run.total_tasks} · {pct}%
          </span>
        </div>
        <Progress value={pct} className="h-2 bg-[#1A1D2B] [&>div]:bg-sky-500" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat icon={Layers} label="Tasks" value={`${run.completed_tasks}/${run.total_tasks}`} testid="stat-tasks" />
        <Stat icon={Repeat} label="Iterations" value={run.iteration_count} testid="stat-iterations" />
        <Stat
          icon={Clock}
          label="Duration"
          value={fmtDuration(run.started_at, run.finished_at)}
          testid="stat-duration"
        />
        <Stat
          icon={Layers}
          label="Active agent"
          value={run.active_agent || "—"}
          testid="stat-agent"
          accent
        />
      </div>

      {run.error && (
        <div
          className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300 font-mono"
          data-testid="run-error"
        >
          {run.error}
        </div>
      )}
    </div>
  );
}

function Stat({ icon: Icon, label, value, testid, accent }) {
  return (
    <div className="rounded-lg border border-[#2A2E43] bg-[#0F111A] px-4 py-3" data-testid={testid}>
      <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-500">
        <Icon className="w-3.5 h-3.5" /> {label}
      </div>
      <p className={`font-heading font-semibold mt-1 truncate capitalize ${accent ? "text-sky-400" : "text-slate-100"}`}>
        {value}
      </p>
    </div>
  );
}
