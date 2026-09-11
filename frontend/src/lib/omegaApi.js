import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const omega = {
  health: () => axios.get(`${API}/omega/health`).then((r) => r.data),
  config: () => axios.get(`${API}/omega/config`).then((r) => r.data),
  startRun: (payload) => axios.post(`${API}/omega/runs`, payload).then((r) => r.data),
  listRuns: () => axios.get(`${API}/omega/runs`).then((r) => r.data),
  getRun: (id) => axios.get(`${API}/omega/runs/${id}`).then((r) => r.data),
  getLogs: (id, after = 0) =>
    axios.get(`${API}/omega/runs/${id}/logs?after=${after}`).then((r) => r.data),
  getFiles: (id) => axios.get(`${API}/omega/runs/${id}/files`).then((r) => r.data),
  getFile: (id, path) =>
    axios.get(`${API}/omega/runs/${id}/file?path=${encodeURIComponent(path)}`).then((r) => r.data),
  stopRun: (id) => axios.post(`${API}/omega/runs/${id}/stop`).then((r) => r.data),
  deleteRun: (id) => axios.delete(`${API}/omega/runs/${id}`).then((r) => r.data),
};

export const SAMPLE_PRD = `# Task Tracker

A lightweight command-line task tracker that lets users add tasks, list them, and mark them as done.

## Goals
- Store tasks in memory during a session
- Provide add / list / complete operations
- Ship with unit tests and a runnable entry point

## Functional Requirements
- \`add(title)\` creates a task
- \`list()\` returns all tasks
- \`complete(id)\` marks a task done

## Tech Stack
- Python 3.10+
- pytest for tests
`;
