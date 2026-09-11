import { useEffect, useMemo, useRef, useState } from "react";
import { Search, ChevronRight, Terminal } from "lucide-react";
import { Input } from "../ui/input";
import { LOG_COLORS } from "./meta";

const LEVELS = ["ALL", "INFO", "DEBUG", "WARNING", "ERROR"];

export default function LogStream({ logs }) {
  const [level, setLevel] = useState("ALL");
  const [query, setQuery] = useState("");
  const [autoscroll, setAutoscroll] = useState(true);
  const [expanded, setExpanded] = useState({});
  const endRef = useRef(null);

  const filtered = useMemo(() => {
    return (logs || []).filter((l) => {
      if (level !== "ALL" && l.level !== level) return false;
      if (query && !`${l.message} ${l.phase} ${l.task_id || ""}`.toLowerCase().includes(query.toLowerCase()))
        return false;
      return true;
    });
  }, [logs, level, query]);

  useEffect(() => {
    if (autoscroll && endRef.current) endRef.current.scrollIntoView({ behavior: "smooth" });
  }, [filtered.length, autoscroll]);

  return (
    <div className="rounded-xl border border-[#2A2E43] bg-[#06070B] overflow-hidden" data-testid="realtime-log-stream">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b border-[#2A2E43] bg-[#0B0D14]">
        <Terminal className="w-4 h-4 text-sky-400" />
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400 mr-2">omega.log</span>
        <div className="flex gap-1">
          {LEVELS.map((lv) => (
            <button
              key={lv}
              onClick={() => setLevel(lv)}
              className={`text-[10px] font-mono uppercase px-2 py-1 rounded transition-colors ${
                level === lv ? "bg-sky-500 text-[#090A0F]" : "text-slate-400 hover:text-sky-400 hover:bg-[#1A1D2B]"
              }`}
              data-testid={`log-filter-${lv}`}
            >
              {lv}
            </button>
          ))}
        </div>
        <div className="relative ml-auto">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="filter…"
            className="h-8 w-40 pl-8 bg-[#06070B] border-[#2A2E43] text-slate-200 font-mono text-xs focus-visible:ring-sky-400"
            data-testid="log-search-input"
          />
        </div>
        <label className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoscroll}
            onChange={(e) => setAutoscroll(e.target.checked)}
            className="accent-sky-500"
          />
          auto
        </label>
      </div>

      <div className="p-3 font-mono text-[12px] leading-relaxed overflow-auto max-h-[560px] scroll-smooth">
        {filtered.length === 0 && (
          <div className="text-slate-600 text-center py-8">no log entries</div>
        )}
        {filtered.map((l) => (
          <div key={l.seq} className="py-0.5" data-testid="log-line">
            <div className="flex items-start gap-2">
              <span className="text-slate-600 shrink-0">{fmtTime(l.ts)}</span>
              <span className="shrink-0 w-16" style={{ color: LOG_COLORS[l.level] || "#94A3B8" }}>
                {l.level}
              </span>
              <span className="text-purple-400 shrink-0 w-24 truncate">{l.phase}</span>
              {l.task_id && <span className="text-amber-400 shrink-0">{l.task_id}</span>}
              <span className="text-slate-300 break-words">{l.message}</span>
              {(l.raw_response || l.details) && (
                <button
                  onClick={() => setExpanded((e) => ({ ...e, [l.seq]: !e[l.seq] }))}
                  className="ml-auto text-slate-500 hover:text-sky-400 shrink-0"
                  title="toggle raw"
                >
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${expanded[l.seq] ? "rotate-90" : ""}`} />
                </button>
              )}
            </div>
            {expanded[l.seq] && (
              <pre className="mt-1 ml-24 p-2 rounded bg-[#0B0D14] border border-[#2A2E43] text-slate-400 text-[11px] whitespace-pre-wrap break-words max-h-64 overflow-auto">
                {l.raw_response || (typeof l.details === "string" ? l.details : JSON.stringify(l.details, null, 2))}
              </pre>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function fmtTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString("en-GB", { hour12: false });
  } catch {
    return "";
  }
}
