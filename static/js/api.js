// Lightweight fetch wrappers for the Gantt API.
const API = (() => {
  async function req(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || res.statusText;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  return {
    listSchedules: () => req('GET', '/api/schedules'),
    createSchedule: (data) => req('POST', '/api/schedules', data),
    getSchedule: (id) => req('GET', `/api/schedules/${id}`),
    updateSchedule: (id, data) => req('PATCH', `/api/schedules/${id}`, data),
    deleteSchedule: (id) => req('DELETE', `/api/schedules/${id}`),

    listTasks: (sid) => req('GET', `/api/schedules/${sid}/tasks`),
    createTask: (sid, data) => req('POST', `/api/schedules/${sid}/tasks`, data),
    updateTask: (id, data) => req('PATCH', `/api/tasks/${id}`, data),
    deleteTask: (id) => req('DELETE', `/api/tasks/${id}`),

    addDependency: (taskId, prereqId) =>
      req('POST', `/api/tasks/${taskId}/dependencies`, { prerequisite_id: prereqId }),
    deleteDependency: (depId) => req('DELETE', `/api/dependencies/${depId}`),
  };
})();
