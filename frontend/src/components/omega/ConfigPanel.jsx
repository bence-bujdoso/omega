import { Settings2 } from "lucide-react";
import { Card } from "../ui/card";

export default function ConfigPanel({ run }) {
  const cfg = run?.config;
  if (!cfg) {
    return (
      <div
        className="rounded-xl border border-[#2A2E43] bg-[#0F111A] p-10 text-center text-slate-500 font-mono text-sm"
        data-testid="config-settings-panel"
      >
        Config unavailable.
      </div>
    );
  }
  const models = cfg.models?.default || {};
  const iter = cfg.iteration || {};
  const sb = cfg.sandbox || {};
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="config-settings-panel">
      <div className="space-y-4">
        <Card className="bg-[#12141D] border-[#2A2E43] p-5">
          <h3 className="font-heading font-semibold flex items-center gap-2 text-sm mb-3">
            <Settings2 className="w-4 h-4 text-sky-400" /> LLM Provider
          </h3>
          <dl className="space-y-2 text-sm">
            <Row k="Provider" v={models.provider} />
            <Row k="Model" v={models.model} mono />
            <Row k="Base URL" v={models.base_url} mono />
            <Row k="API key env" v={models.api_key_env} mono />
            <Row k="Temperature" v={models.temperature} mono />
            <Row k="Max tokens" v={models.max_tokens} mono />
          </dl>
        </Card>
        <Card className="bg-[#12141D] border-[#2A2E43] p-5">
          <h3 className="font-heading font-semibold text-sm mb-3">Iteration & Sandbox</h3>
          <dl className="space-y-2 text-sm">
            <Row k="Auto fix" v={String(iter.auto_fix)} mono />
            <Row k="Max per task" v={iter.max_per_task} mono />
            <Row k="Max global" v={iter.max_global} mono />
            <Row k="Require tests" v={String(iter.require_tests)} mono />
            <Row k="Sandbox type" v={sb.type} mono />
            <Row k="Sandbox timeout" v={`${sb.timeout}s`} mono />
          </dl>
        </Card>
      </div>

      <Card className="bg-[#06070B] border-[#2A2E43] p-0 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#2A2E43]">
          <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">omega.yaml</span>
        </div>
        <pre className="p-4 text-[12px] leading-relaxed font-mono text-slate-300 overflow-auto max-h-[560px]" data-testid="config-json">
          {JSON.stringify(cfg, null, 2)}
        </pre>
      </Card>
    </div>
  );
}

function Row({ k, v, mono }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-slate-500 text-xs uppercase font-mono tracking-wider shrink-0">{k}</dt>
      <dd className={`text-slate-200 text-right truncate ${mono ? "font-mono text-[13px]" : ""}`}>{v ?? "—"}</dd>
    </div>
  );
}
