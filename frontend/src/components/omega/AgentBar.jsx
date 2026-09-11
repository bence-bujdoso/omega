import { Compass, ListTree, Code2, ScanSearch, Wrench } from "lucide-react";
import { AGENTS } from "./meta";

const ICONS = { Compass, ListTree, Code2, ScanSearch, Wrench };

export default function AgentBar({ run }) {
  const active = run?.active_agent;
  return (
    <div
      className="flex flex-wrap gap-2 sm:gap-3"
      data-testid="agent-activity-indicators"
    >
      {AGENTS.map((a) => {
        const Icon = ICONS[a.icon];
        const isActive = active === a.key;
        return (
          <div
            key={a.key}
            className={`relative flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border transition-all duration-300 ${
              isActive
                ? "border-transparent bg-[#12141D] scale-[1.03]"
                : "border-[#2A2E43] bg-[#0F111A] opacity-70"
            }`}
            style={isActive ? { boxShadow: `0 0 0 1px ${a.color}66, 0 0 22px ${a.color}33` } : {}}
            data-testid={`agent-${a.key}`}
            data-active={isActive}
          >
            <div className="relative">
              {isActive && <span className="glow-ring" style={{ background: "transparent" }} />}
              <span
                className="w-8 h-8 rounded-lg grid place-items-center relative"
                style={{ background: `${a.color}1f`, color: a.color }}
              >
                <Icon className="w-4 h-4" strokeWidth={2} />
                {isActive && (
                  <span
                    className="absolute inset-0 rounded-lg animate-ping"
                    style={{ background: `${a.color}25` }}
                  />
                )}
              </span>
            </div>
            <div className="leading-tight">
              <p
                className="text-sm font-medium"
                style={{ color: isActive ? a.color : "#CBD5E1" }}
              >
                {a.label}
              </p>
              <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                {isActive ? "active" : "idle"}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
