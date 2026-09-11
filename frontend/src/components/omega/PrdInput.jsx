import { useState } from "react";
import { FileText, Play, Sparkles, Cpu, Boxes, ChevronRight } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Card } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { SAMPLE_PRD } from "../../lib/omegaApi";
import { STATUS_META, fmtDuration } from "./meta";

export default function PrdInput({ onStart, runs, onOpenRun, health }) {
  const [prd, setPrd] = useState("");
  const [name, setName] = useState("");
  const [sandbox, setSandbox] = useState("process");
  const [maxPerTask, setMaxPerTask] = useState(30);
  const [maxGlobal, setMaxGlobal] = useState(30);
  const [refineIterations, setRefineIterations] = useState(2);
  const [busy, setBusy] = useState(false);

  const deriveName = (text) => {
    const m = (text || "").split("\n").find((l) => l.trim().startsWith("# "));
    return m ? m.replace("# ", "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") : "";
  };

  const start = async () => {
    if (!prd.trim()) return;
    setBusy(true);
    await onStart({
      prd,
      project_name: name || deriveName(prd) || "omega-project",
      sandbox_type: sandbox,
      max_per_task: Number(maxPerTask),
      max_global: Number(maxGlobal),
      refine_iterations: Math.max(0, parseInt(refineIterations, 10) || 0),
    });
    setBusy(false);
  };

  const loadSample = () => {
    setPrd(SAMPLE_PRD);
    setName("task-tracker");
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-up" data-testid="prd-input-section">
      <div className="lg:col-span-8 space-y-5">
        <div>
          <h2 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight">
            Turn a <span className="text-sky-400">PRD</span> into a running product.
          </h2>
          <p className="text-slate-400 mt-2 text-sm sm:text-base max-w-2xl">
            Paste a markdown Product Requirements Document. Omega's agents — Architect, Planner,
            Coder, Reviewer and Fixer — decompose, build, validate and iterate until it runs.
          </p>
        </div>

        <Card className="bg-[#12141D] border-[#2A2E43] p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#2A2E43] bg-[#0F111A]">
            <div className="flex items-center gap-2 text-slate-300">
              <FileText className="w-4 h-4 text-sky-400" />
              <span className="font-mono text-xs uppercase tracking-wider">prd.md</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadSample}
              className="text-sky-400 hover:text-sky-300 hover:bg-[#1A1D2B] gap-1.5 h-8"
              data-testid="load-sample-btn"
            >
              <Sparkles className="w-3.5 h-3.5" /> Load sample
            </Button>
          </div>
          <Textarea
            value={prd}
            onChange={(e) => setPrd(e.target.value)}
            placeholder={"# My Product\n\nDescribe what to build…"}
            className="min-h-[360px] rounded-none border-0 bg-[#06070B] font-mono text-[13px] leading-relaxed text-slate-200 resize-y focus-visible:ring-0 focus-visible:ring-offset-0"
            data-testid="prd-textarea"
          />
        </Card>
      </div>

      <div className="lg:col-span-4 space-y-5">
        <Card className="bg-[#12141D] border-[#2A2E43] p-5 space-y-4">
          <h3 className="font-heading font-semibold flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" /> Pipeline Config
          </h3>

          <div className="space-y-1.5">
            <label className="text-xs text-slate-400 font-mono uppercase tracking-wider">Project name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="auto from PRD heading"
              className="bg-[#06070B] border-[#2A2E43] text-slate-200 focus-visible:ring-sky-400"
              data-testid="project-name-input"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-slate-400 font-mono uppercase tracking-wider">Sandbox</label>
            <Select value={sandbox} onValueChange={setSandbox}>
              <SelectTrigger
                className="bg-[#06070B] border-[#2A2E43] text-slate-200"
                data-testid="sandbox-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#12141D] border-[#2A2E43] text-slate-200">
                <SelectItem value="process">Process (fast, local)</SelectItem>
                <SelectItem value="docker">Docker (isolated)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-mono uppercase tracking-wider">Max fix iterations / task</label>
              <Input
                type="number"
                value={maxPerTask}
                onChange={(e) => setMaxPerTask(e.target.value)}
                className="bg-[#06070B] border-[#2A2E43] text-slate-200 font-mono"
                data-testid="max-per-task-input"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-mono uppercase tracking-wider">Max global</label>
              <Input
                type="number"
                value={maxGlobal}
                onChange={(e) => setMaxGlobal(e.target.value)}
                className="bg-[#06070B] border-[#2A2E43] text-slate-200 font-mono"
                data-testid="max-global-input"
              />
            </div>
          </div>

          <div className="space-y-1.5 rounded-lg border border-purple-500/30 bg-purple-500/5 p-3">
            <label className="text-xs text-purple-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Refinement passes
            </label>
            <Input
              type="number"
              min="0"
              step="1"
              value={refineIterations}
              onChange={(e) => setRefineIterations(e.target.value)}
              className="bg-[#06070B] border-purple-500/40 text-purple-100 font-mono focus-visible:ring-purple-400"
              data-testid="refine-iterations-input"
            />
            <p className="text-[11px] text-slate-500 leading-relaxed">
              After the build, the Reviewer + Fixer polish the whole product this many times to lift
              overall quality. Any positive number is allowed; 0 = ship as built.
            </p>
          </div>

          <div className="text-[11px] font-mono text-slate-500 flex items-center gap-2 pt-1">
            <Boxes className="w-3.5 h-3.5" />
            {health?.llm?.model || "9router-combo"} · {health?.llm?.provider || "openai"}
          </div>

          <Button
            onClick={start}
            disabled={!prd.trim() || busy}
            className="w-full bg-sky-500 hover:bg-sky-400 text-[#090A0F] font-semibold gap-2 h-11"
            data-testid="start-pipeline-btn"
          >
            <Play className="w-4 h-4" /> {busy ? "Starting…" : "Start Pipeline"}
          </Button>
        </Card>

        {runs?.length > 0 && (
          <Card className="bg-[#12141D] border-[#2A2E43] p-5">
            <h3 className="font-heading font-semibold mb-3 text-sm">Recent Runs</h3>
            <div className="space-y-2" data-testid="recent-runs">
              {runs.slice(0, 5).map((r) => {
                const meta = STATUS_META[r.status] || STATUS_META.pending;
                return (
                  <button
                    key={r.id}
                    onClick={() => onOpenRun(r.id)}
                    className="w-full flex items-center justify-between text-left px-3 py-2 rounded-lg border border-[#2A2E43] bg-[#0F111A] hover:border-sky-500/50 hover:bg-[#1A1D2B] transition-all group"
                    data-testid={`recent-run-${r.id}`}
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-slate-200 truncate font-medium">{r.project_name}</p>
                      <p className="text-[11px] font-mono text-slate-500">
                        {r.completed_tasks}/{r.total_tasks} tasks · {fmtDuration(r.started_at, r.finished_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className="text-[10px] font-mono uppercase px-2 py-0.5 rounded"
                        style={{ color: meta.color, background: meta.bg }}
                      >
                        {meta.label}
                      </span>
                      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-sky-400" />
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
