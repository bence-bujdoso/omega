import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Hexagon, Plus, Activity, History, Radio } from "lucide-react";
import { Button } from "../ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "../ui/sheet";
import { omega } from "../../lib/omegaApi";
import PrdInput from "./PrdInput";
import RunView from "./RunView";
import RunsHistory from "./RunsHistory";

const ACTIVE_STATES = ["pending", "planning", "coding"];

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [runs, setRuns] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [run, setRun] = useState(null);
  const [logs, setLogs] = useState([]);
  const [files, setFiles] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const lastSeq = useRef(0);
  const pollRef = useRef(null);

  const refreshRuns = useCallback(() => omega.listRuns().then(setRuns).catch(() => {}), []);

  useEffect(() => {
    omega.health().then(setHealth).catch(() => {});
    refreshRuns();
  }, [refreshRuns]);

  const loadRun = useCallback(async (id) => {
    try {
      const r = await omega.getRun(id);
      setRun(r);
      const newLogs = await omega.getLogs(id, lastSeq.current);
      if (newLogs.length) {
        lastSeq.current = newLogs[newLogs.length - 1].seq;
        setLogs((prev) => [...prev, ...newLogs]);
      }
      const f = await omega.getFiles(id);
      setFiles(f.files || []);
      return r;
    } catch (e) {
      return null;
    }
  }, []);

  // polling loop
  useEffect(() => {
    if (!currentId) return;
    const tick = async () => {
      const r = await loadRun(currentId);
      if (r && !ACTIVE_STATES.includes(r.status)) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        refreshRuns();
      }
    };
    tick();
    pollRef.current = setInterval(tick, 1300);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [currentId, loadRun, refreshRuns]);

  const handleStart = async (payload) => {
    try {
      const res = await omega.startRun(payload);
      lastSeq.current = 0;
      setLogs([]);
      setFiles([]);
      setRun(null);
      setCurrentId(res.id);
      toast.success("Pipeline started", { description: payload.project_name });
      refreshRuns();
    } catch (e) {
      toast.error("Failed to start pipeline", { description: e?.response?.data?.detail || e.message });
    }
  };

  const openRun = async (id) => {
    lastSeq.current = 0;
    setLogs([]);
    setFiles([]);
    setRun(null);
    setCurrentId(id);
    setHistoryOpen(false);
  };

  const newRun = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setCurrentId(null);
    setRun(null);
    setLogs([]);
    setFiles([]);
    lastSeq.current = 0;
  };

  const stop = async () => {
    if (!currentId) return;
    try {
      await omega.stopRun(currentId);
      toast.message("Stopping pipeline…");
    } catch (e) {
      toast.error("Nothing to stop");
    }
  };

  return (
    <div className="min-h-screen" data-testid="omega-dashboard">
      <header
        className="sticky top-0 z-30 backdrop-blur-xl bg-[#0B0D14]/85 border-b border-[#2A2E43]"
        data-testid="omega-header"
      >
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Hexagon className="w-8 h-8 text-sky-400" strokeWidth={1.5} />
              <span className="absolute inset-0 flex items-center justify-center font-heading font-bold text-[10px] text-sky-300">
                Ω
              </span>
            </div>
            <div>
              <h1 className="font-heading font-bold text-lg leading-none tracking-tight">Omega</h1>
              <p className="text-[11px] text-slate-500 font-mono">PRD → PRODUCT PIPELINE</p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <HealthPill health={health} />
            <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="outline"
                  className="border-[#2A2E43] bg-transparent hover:bg-[#1A1D2B] hover:text-sky-400 text-slate-300 gap-2"
                  data-testid="open-history-btn"
                >
                  <History className="w-4 h-4" /> <span className="hidden sm:inline">Runs</span>
                </Button>
              </SheetTrigger>
              <SheetContent className="bg-[#0B0D14] border-l border-[#2A2E43] text-slate-100 w-full sm:max-w-md p-0">
                <SheetHeader className="p-5 border-b border-[#2A2E43]">
                  <SheetTitle className="font-heading text-slate-100">Runs History</SheetTitle>
                </SheetHeader>
                <RunsHistory runs={runs} currentId={currentId} onOpen={openRun} onRefresh={refreshRuns} />
              </SheetContent>
            </Sheet>
            <Button
              onClick={newRun}
              className="bg-sky-500 hover:bg-sky-400 text-[#090A0F] font-semibold gap-2"
              data-testid="new-run-btn"
            >
              <Plus className="w-4 h-4" /> <span className="hidden sm:inline">New Run</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {!currentId ? (
          <PrdInput onStart={handleStart} runs={runs} onOpenRun={openRun} health={health} />
        ) : (
          <RunView run={run} logs={logs} files={files} currentId={currentId} onStop={stop} />
        )}
      </main>
    </div>
  );
}

function HealthPill({ health }) {
  const ok = health?.ok;
  return (
    <div
      className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#2A2E43] bg-[#12141D]"
      data-testid="health-pill"
      title={health ? `LLM: ${health.llm?.model} @ ${health.llm?.base_url}` : "checking"}
    >
      {ok ? (
        <Radio className="w-3.5 h-3.5 text-emerald-400" />
      ) : (
        <Activity className="w-3.5 h-3.5 text-amber-400" />
      )}
      <span className="text-[11px] font-mono text-slate-400">
        {health ? (health.llm?.api_key_present ? "9router live" : "offline engine") : "…"}
      </span>
    </div>
  );
}
