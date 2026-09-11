import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import PipelineHeader from "./PipelineHeader";
import AgentBar from "./AgentBar";
import KanbanBoard from "./KanbanBoard";
import ArchitectureView from "./ArchitectureView";
import LogStream from "./LogStream";
import FileExplorer from "./FileExplorer";
import ConfigPanel from "./ConfigPanel";
import PromptAnalytics from "./PromptAnalytics";
import { LayoutGrid, Boxes, Terminal, FolderTree, Settings2, BarChart3 } from "lucide-react";

const TABS = [
  { key: "kanban", label: "Kanban", icon: LayoutGrid },
  { key: "architecture", label: "Architecture", icon: Boxes },
  { key: "logs", label: "Logs", icon: Terminal },
  { key: "files", label: "Files", icon: FolderTree },
  { key: "prompts", label: "Prompts", icon: BarChart3 },
  { key: "config", label: "Config", icon: Settings2 },
];

export default function RunView({ run, logs, files, currentId, onStop }) {
  return (
    <div className="space-y-6 animate-fade-up" data-testid="run-view">
      <PipelineHeader run={run} onStop={onStop} />
      <AgentBar run={run} />

      <Tabs defaultValue="kanban" className="w-full">
        <TabsList className="bg-[#12141D] border border-[#2A2E43] p-1 h-auto flex flex-wrap gap-1">
          {TABS.map(({ key, label, icon: Icon }) => (
            <TabsTrigger
              key={key}
              value={key}
              className="data-[state=active]:bg-sky-500 data-[state=active]:text-[#090A0F] text-slate-400 gap-2 px-4 py-2"
              data-testid={`tab-${key}`}
            >
              <Icon className="w-4 h-4" /> {label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="kanban" className="mt-5">
          <KanbanBoard run={run} />
        </TabsContent>
        <TabsContent value="architecture" className="mt-5">
          <ArchitectureView run={run} />
        </TabsContent>
        <TabsContent value="logs" className="mt-5">
          <LogStream logs={logs} />
        </TabsContent>
        <TabsContent value="files" className="mt-5">
          <FileExplorer files={files} currentId={currentId} />
        </TabsContent>
        <TabsContent value="prompts" className="mt-5">
          <PromptAnalytics run={run} />
        </TabsContent>
        <TabsContent value="config" className="mt-5">
          <ConfigPanel run={run} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
