import { BarChart3, CheckCircle2, Ban, Repeat } from "lucide-react";
import { Card } from "../ui/card";
import { agentColor } from "./meta";

const ORDER = ["architect", "planner", "coder", "tester", "debugger", "reviewer", "fixer"];

export default function PromptAnalytics({ run }) {
  const stats = run?.prompt_stats || {};
  const names = Object.keys(stats).sort(
    (a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99)
  );

  if (names.length === 0) {
    return (
      <div
        className="rounded-xl border border-[#2A2E43] bg-[#0F111A] p-10 text-center text-slate-500 font-mono text-sm"
        data-testid="prompt-analytics-panel"
      >
        No prompt activity yet. Analytics populate as agents run.
      </div>
    );
  }

  const totalRuns = names.reduce((s, n) => s + stats[n].reduce((a, v) => a + v.runs, 0), 0);
  const disabledCount = names.reduce(
    (s, n) => s + stats[n].filter((v) => v.disabled).length,
    0
  );

  return (
    <div className="space-y-4" data-testid="prompt-analytics-panel">
      <div className="grid grid-cols-3 gap-3">
        <Summary icon={BarChart3} label="Prompts tracked" value={names.length} />
        <Summary icon={Repeat} label="Total invocations" value={totalRuns} />
        <Summary icon={Ban} label="Auto-disabled" value={disabledCount} accent={disabledCount > 0} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {names.map((name) => {
          const versions = stats[name] || [];
          const color = agentColor(name);
          return (
            <Card
              key={name}
              className="bg-[#12141D] border-[#2A2E43] p-5"
              data-testid={`prompt-card-${name}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: color }}
                  />
                  <h3 className="font-heading font-semibold capitalize">{name}</h3>
                </div>
                <span className="text-[10px] font-mono uppercase text-slate-500">
                  {versions.length} ver
                </span>
              </div>

              <div className="space-y-3">
                {versions.map((v) => {
                  const rate = Math.round((v.success_rate ?? 1) * 100);
                  return (
                    <div key={v.version} data-testid={`prompt-version-${name}-${v.version}`}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-mono text-slate-400">{v.version}</span>
                        {v.disabled ? (
                          <span className="flex items-center gap-1 text-[10px] font-mono uppercase text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded">
                            <Ban className="w-3 h-3" /> disabled
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[10px] font-mono uppercase text-emerald-400">
                            <CheckCircle2 className="w-3 h-3" /> active
                          </span>
                        )}
                      </div>
                      <div className="h-2 rounded-full bg-[#1A1D2B] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${rate}%`,
                            background: v.disabled ? "#F43F5E" : color,
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-between mt-1 text-[11px] font-mono text-slate-500">
                        <span>{rate}% success</span>
                        <span>
                          {v.successes}/{v.runs} runs
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="text-[10px] font-mono text-slate-600 mt-3 leading-relaxed">
                Auto-disables below 40% success after 5+ runs.
              </p>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function Summary({ icon: Icon, label, value, accent }) {
  return (
    <div className="rounded-lg border border-[#2A2E43] bg-[#0F111A] px-4 py-3">
      <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-500">
        <Icon className="w-3.5 h-3.5" /> {label}
      </div>
      <p className={`font-heading font-semibold text-xl mt-1 ${accent ? "text-rose-400" : "text-slate-100"}`}>
        {value}
      </p>
    </div>
  );
}
