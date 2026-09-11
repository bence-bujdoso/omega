// shared UI helpers for Omega dashboard
export const AGENTS = [
  { key: "architect", label: "Architect", color: "#8B5CF6", icon: "Compass" },
  { key: "planner", label: "Planner", color: "#06B6D4", icon: "ListTree" },
  { key: "coder", label: "Coder", color: "#38BDF8", icon: "Code2" },
  { key: "reviewer", label: "Reviewer", color: "#F59E0B", icon: "ScanSearch" },
  { key: "fixer", label: "Fixer", color: "#10B981", icon: "Wrench" },
];

export const PHASES = [
  { key: "architecture", label: "Architecture" },
  { key: "planning", label: "Planning" },
  { key: "coding", label: "Coding" },
  { key: "done", label: "Done" },
];

export const STATUS_META = {
  pending: { label: "Pending", color: "#94A3B8", bg: "rgba(148,163,184,0.12)" },
  planning: { label: "Planning", color: "#06B6D4", bg: "rgba(6,182,212,0.12)" },
  coding: { label: "Coding", color: "#F59E0B", bg: "rgba(245,158,11,0.12)" },
  done: { label: "Done", color: "#10B981", bg: "rgba(16,185,129,0.14)" },
  failed: { label: "Failed", color: "#F43F5E", bg: "rgba(244,63,94,0.14)" },
};

export const TASK_STATUS = {
  TODO: { color: "#94A3B8", bg: "rgba(148,163,184,0.12)" },
  IN_PROGRESS: { color: "#F59E0B", bg: "rgba(245,158,11,0.14)" },
  REVIEW: { color: "#A855F7", bg: "rgba(168,85,247,0.14)" },
  DONE: { color: "#10B981", bg: "rgba(16,185,129,0.16)" },
  FAILED: { color: "#F43F5E", bg: "rgba(244,63,94,0.16)" },
  BLOCKED: { color: "#F43F5E", bg: "rgba(244,63,94,0.12)" },
};

export const LOG_COLORS = {
  DEBUG: "#64748B",
  INFO: "#38BDF8",
  WARNING: "#F59E0B",
  ERROR: "#F43F5E",
};

export const agentColor = (key) =>
  (AGENTS.find((a) => a.key === key) || { color: "#94A3B8" }).color;

export function fmtDuration(start, end) {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const secs = Math.max(0, Math.round((e - s) / 1000));
  return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
}
