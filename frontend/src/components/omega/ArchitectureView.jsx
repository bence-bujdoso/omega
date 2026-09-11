import { Boxes, Package, FileCode2, Terminal, Layers } from "lucide-react";
import { Card } from "../ui/card";

export default function ArchitectureView({ run }) {
  const arch = run?.architecture;
  if (!arch) {
    return (
      <div
        className="rounded-xl border border-[#2A2E43] bg-[#0F111A] p-10 text-center text-slate-500 font-mono text-sm"
        data-testid="architecture-spec-container"
      >
        Waiting for the Architect agent to produce the architecture spec…
      </div>
    );
  }
  const ts = arch.tech_stack || {};
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4" data-testid="architecture-spec-container">
      <div className="lg:col-span-4 space-y-4">
        <Card className="bg-[#12141D] border-[#2A2E43] p-5">
          <h3 className="font-heading font-semibold flex items-center gap-2 mb-1">
            <Boxes className="w-4 h-4 text-purple-400" /> {arch.project_name}
          </h3>
          <p className="text-sm text-slate-400 leading-relaxed">{arch.description}</p>
        </Card>

        <Card className="bg-[#12141D] border-[#2A2E43] p-5 space-y-3">
          <h3 className="font-heading font-semibold flex items-center gap-2 text-sm">
            <Layers className="w-4 h-4 text-cyan-400" /> Tech Stack
          </h3>
          <dl className="space-y-2 text-sm">
            <Row k="Language" v={ts.primary_language} />
            <Row k="Framework" v={ts.framework} />
            <Row k="Database" v={ts.database} />
            <Row k="Main module" v={ts.main_module} mono />
          </dl>
          {ts.build_command && (
            <div className="pt-1">
              <p className="text-[11px] font-mono uppercase text-slate-500 mb-1 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5" /> build
              </p>
              <code className="block text-[12px] text-emerald-300 bg-[#06070B] rounded px-2 py-1.5 font-mono break-all">
                {ts.build_command}
              </code>
            </div>
          )}
          {ts.test_command && (
            <div>
              <p className="text-[11px] font-mono uppercase text-slate-500 mb-1 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5" /> test
              </p>
              <code className="block text-[12px] text-sky-300 bg-[#06070B] rounded px-2 py-1.5 font-mono break-all">
                {ts.test_command}
              </code>
            </div>
          )}
          {(arch.key_dependencies || []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {arch.key_dependencies.map((d) => (
                <span
                  key={d}
                  className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 flex items-center gap-1"
                >
                  <Package className="w-3 h-3" /> {d}
                </span>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="lg:col-span-4 space-y-4">
        <Card className="bg-[#12141D] border-[#2A2E43] p-5">
          <h3 className="font-heading font-semibold flex items-center gap-2 text-sm mb-3">
            <FileCode2 className="w-4 h-4 text-sky-400" /> File Structure
          </h3>
          <div className="space-y-1.5">
            {(arch.file_structure || []).map((f) => (
              <div key={f.path} className="flex items-start gap-2 text-sm">
                <span className="font-mono text-sky-300 shrink-0">{f.path}</span>
                <span className="text-slate-500 text-xs mt-0.5 truncate">{f.purpose}</span>
              </div>
            ))}
          </div>
        </Card>
        {(arch.modules || []).length > 0 && (
          <Card className="bg-[#12141D] border-[#2A2E43] p-5">
            <h3 className="font-heading font-semibold text-sm mb-3">Modules</h3>
            <div className="space-y-2">
              {arch.modules.map((m) => (
                <div key={m.name} className="border-l-2 border-purple-500/40 pl-3">
                  <p className="text-sm text-slate-200 font-medium">{m.name}</p>
                  <p className="text-xs text-slate-500">{m.description}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      <div className="lg:col-span-4">
        <Card className="bg-[#06070B] border-[#2A2E43] p-0 h-full overflow-hidden">
          <div className="px-4 py-2.5 border-b border-[#2A2E43] flex items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
              architecture.json
            </span>
          </div>
          <pre
            className="p-4 text-[12px] leading-relaxed font-mono text-slate-300 overflow-auto max-h-[560px]"
            data-testid="architecture-json"
          >
            {JSON.stringify(arch, null, 2)}
          </pre>
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v, mono }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-500 text-xs uppercase font-mono tracking-wider">{k}</dt>
      <dd className={`text-slate-200 ${mono ? "font-mono text-[13px]" : ""}`}>{v || "—"}</dd>
    </div>
  );
}
