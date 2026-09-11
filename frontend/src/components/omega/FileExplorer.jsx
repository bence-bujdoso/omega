import { useEffect, useState } from "react";
import { FileCode2, FileText, FileJson, File, Loader2 } from "lucide-react";
import { omega } from "../../lib/omegaApi";

const iconFor = (path) => {
  if (path.endsWith(".py")) return FileCode2;
  if (path.endsWith(".md")) return FileText;
  if (path.endsWith(".json")) return FileJson;
  return File;
};

export default function FileExplorer({ files, currentId }) {
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  const visible = (files || []).filter((f) => f.path !== "state.json" || true);

  useEffect(() => {
    if (!selected && visible.length) {
      const first = visible.find((f) => f.path.endsWith(".py")) || visible[0];
      setSelected(first.path);
    }
  }, [visible, selected]);

  useEffect(() => {
    if (!selected || !currentId) return;
    setLoading(true);
    omega
      .getFile(currentId, selected)
      .then((d) => setContent(d.content))
      .catch(() => setContent("// unable to load file"))
      .finally(() => setLoading(false));
  }, [selected, currentId]);

  if (!visible.length) {
    return (
      <div
        className="rounded-xl border border-[#2A2E43] bg-[#0F111A] p-10 text-center text-slate-500 font-mono text-sm"
        data-testid="generated-project-explorer"
      >
        No files generated yet. The Coder agent writes files here as tasks complete.
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-1 lg:grid-cols-12 gap-4 rounded-xl border border-[#2A2E43] bg-[#0F111A] overflow-hidden"
      data-testid="generated-project-explorer"
    >
      <div className="lg:col-span-3 border-r border-[#2A2E43] p-3 max-h-[600px] overflow-auto">
        <p className="text-[11px] font-mono uppercase tracking-wider text-slate-500 px-2 mb-2">generated/</p>
        {visible.map((f) => {
          const Icon = iconFor(f.path);
          const active = selected === f.path;
          return (
            <button
              key={f.path}
              onClick={() => setSelected(f.path)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-sm transition-colors ${
                active ? "bg-sky-500/15 text-sky-300" : "text-slate-300 hover:bg-[#1A1D2B] hover:text-sky-400"
              }`}
              data-testid={`file-item-${f.path}`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="font-mono text-[13px] truncate">{f.path}</span>
            </button>
          );
        })}
      </div>

      <div className="lg:col-span-9 bg-[#06070B] min-h-[300px]">
        <div className="px-4 py-2.5 border-b border-[#2A2E43] flex items-center gap-2">
          <span className="font-mono text-[12px] text-slate-400">{selected}</span>
          {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />}
        </div>
        <pre
          className="p-4 text-[12.5px] leading-relaxed font-mono text-slate-200 overflow-auto max-h-[560px]"
          data-testid="file-content"
        >
          {content}
        </pre>
      </div>
    </div>
  );
}
