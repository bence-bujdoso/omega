import { Trash2, ArrowRight, RefreshCw } from "lucide-react";
import { omega } from "../../lib/omegaApi";
import { STATUS_META, fmtDuration } from "./meta";
import { toast } from "sonner";

export default function RunsHistory({ runs, currentId, onOpen, onRefresh }) {
  const remove = async (e, id) => {
    e.stopPropagation();
    try {
      await omega.deleteRun(id);
      toast.success("Run deleted");
      onRefresh();
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="p-4 space-y-2 overflow-auto max-h-[calc(100vh-80px)]" data-testid="runs-history-panel">
      <button
        onClick={onRefresh}
        className="w-full flex items-center justify-center gap-2 text-xs font-mono text-slate-400 hover:text-sky-400 py-2 mb-1"
        data-testid="refresh-runs-btn"
      >
        <RefreshCw className="w-3.5 h-3.5" /> refresh
      </button>
      {(!runs || runs.length === 0) && (
        <p className="text-sm text-slate-500 text-center py-8 font-mono">No runs yet.</p>
      )}
      {(runs || []).map((r) => {
        const meta = STATUS_META[r.status] || STATUS_META.pending;
        const active = r.id === currentId;
        return (
          <div
            key={r.id}
            onClick={() => onOpen(r.id)}
            className={`group cursor-pointer rounded-lg border p-3 transition-all ${
              active ? "border-sky-500/60 bg-[#12141D]" : "border-[#2A2E43] bg-[#0F111A] hover:border-sky-500/40 hover:bg-[#12141D]"
            }`}
            data-testid={`history-run-${r.id}`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-slate-200 truncate">{r.project_name}</p>
              <span
                className="text-[10px] font-mono uppercase px-2 py-0.5 rounded shrink-0"
                style={{ color: meta.color, background: meta.bg }}
              >
                {meta.label}
              </span>
            </div>
            <div className="flex items-center justify-between mt-2">
              <p className="text-[11px] font-mono text-slate-500">
                {r.completed_tasks}/{r.total_tasks} tasks · {fmtDuration(r.started_at, r.finished_at)}
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => remove(e, r.id)}
                  className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10"
                  data-testid={`delete-run-${r.id}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-sky-400" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
