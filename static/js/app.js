// App-level UI wiring: schedule list, modals, mode toggle, task editing.
(function () {
  const TAB_SESSION_KEY = 'cg-gantt-tab-session-id';

  const state = {
    schedules: [],
    currentScheduleId: null,
    currentSchedule: null,
    tasks: [],
    editingTask: null, // task object or null (when null = creating)
    labelMode: 'name', // 'name' | 'duration' | 'none'
    buffer: 4,
  };

  let scheduleClickTimer = null;

  const tabSessionId = (() => {
    if (window.sessionStorage && sessionStorage.getItem(TAB_SESSION_KEY)) {
      return sessionStorage.getItem(TAB_SESSION_KEY);
    }
    const id = (window.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    if (window.sessionStorage) sessionStorage.setItem(TAB_SESSION_KEY, id);
    return id;
  })();

  // ---------- Helpers ----------
  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.from(document.querySelectorAll(sel)); }

  function toast(msg, isError) {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.toggle('error', !!isError);
    el.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove('show'), 2400);
  }

  function openModal(id) { $('#' + id).classList.remove('hidden'); }
  function closeModal(id) { $('#' + id).classList.add('hidden'); }

  function sendSessionHeartbeat() {
    fetch(`/api/session/heartbeat?sid=${encodeURIComponent(tabSessionId)}`, {
      method: 'POST',
      keepalive: true,
    }).catch(() => {});
  }

  function sendSessionClose() {
    const url = `/api/session/close?sid=${encodeURIComponent(tabSessionId)}`;
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url);
      return;
    }
    fetch(url, { method: 'POST', keepalive: true }).catch(() => {});
  }

  // Bind generic close buttons
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-close]');
    if (t) closeModal(t.dataset.close);
  });

  // ---------- Schedules ----------
  async function loadSchedules() {
    state.schedules = await API.listSchedules();
    renderScheduleList();
    if (!state.currentScheduleId && state.schedules.length) {
      selectSchedule(state.schedules[0].id);
    } else if (!state.schedules.length) {
      state.currentScheduleId = null;
      state.currentSchedule = null;
      renderEmpty();
    }
  }

  function renderScheduleList() {
    const ul = $('#schedule-list');
    ul.innerHTML = '';
    state.schedules.forEach((s) => {
      const li = document.createElement('li');
      li.dataset.id = s.id;
      li.title = 'Double-click to rename schedule';
      if (s.id === state.currentScheduleId) li.classList.add('active');
      li.innerHTML = `<span>${escapeHtml(s.name)}</span>
                      <div class="actions">
                        <button class="del" title="Delete">×</button>
                      </div>`;
      li.addEventListener('click', (e) => {
        if (e.target.classList.contains('del')) {
          e.stopPropagation();
          if (scheduleClickTimer) {
            clearTimeout(scheduleClickTimer);
            scheduleClickTimer = null;
          }
          if (confirm(`Delete schedule "${s.name}"?`)) deleteSchedule(s.id);
        } else {
          if (scheduleClickTimer) clearTimeout(scheduleClickTimer);
          scheduleClickTimer = setTimeout(() => {
            if (state.currentScheduleId !== s.id) {
              selectSchedule(s.id);
            }
            scheduleClickTimer = null;
          }, 320);
        }
      });
      li.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('del')) return;
        e.preventDefault();
        if (scheduleClickTimer) {
          clearTimeout(scheduleClickTimer);
          scheduleClickTimer = null;
        }
        renameSchedule(s);
      });
      ul.appendChild(li);
    });
  }

  async function selectSchedule(id) {
    state.currentScheduleId = id;
    state.currentSchedule = await API.getSchedule(id);
    state.tasks = state.currentSchedule.tasks || [];
    renderScheduleList();
    renderToolbar();
    renderGantt();
  }

  async function deleteSchedule(id) {
    await API.deleteSchedule(id);
    if (state.currentScheduleId === id) {
      state.currentScheduleId = null;
      state.currentSchedule = null;
    }
    await loadSchedules();
  }

  async function renameSchedule(schedule) {
    const next = prompt('Enter a new schedule name:', schedule.name);
    if (next === null) return;
    const name = next.trim();
    if (!name) {
      toast('Name is required', true);
      return;
    }
    try {
      await API.updateSchedule(schedule.id, { name });
      await loadSchedules();
      if (state.currentScheduleId === schedule.id) {
        await selectSchedule(schedule.id);
      }
      toast('Schedule renamed');
    } catch (e) {
      toast(e.message, true);
    }
  }

  function renderToolbar() {
    const s = state.currentSchedule;
    $('#schedule-title').textContent = s
      ? `${s.name}  ·  starts ${s.start_date}`
      : 'No schedule selected';
    $('#rename-schedule-btn').disabled = !s;
    $('#add-task-btn').disabled = !s;
    $$('#mode-toggle button').forEach((b) => {
      b.classList.toggle('active', s && b.dataset.mode === s.mode);
    });
  }

  function renderEmpty() {
    const wrap = $('#gantt-wrap');
    wrap.innerHTML = '<div class="empty-state"><div>Create or select a schedule to get started.</div></div>';
    renderToolbar();
    renderScheduleList();
  }

  // ---------- Gantt ----------
  function renderGantt() {
    const wrap = $('#gantt-wrap');
    wrap.innerHTML = '';
    if (!state.currentSchedule) { renderEmpty(); return; }
    if (!state.tasks.length) {
      wrap.innerHTML = '<div class="empty-state"><div>No tasks yet. Click "+ Add Task" to start.</div></div>';
      return;
    }
    Gantt.configure({
      onTaskUpdate: async (task, patch) => {
        try {
          await API.updateTask(task.id, patch);
        } catch (e) { toast(e.message, true); }
      },
      onTaskClick: (task) => openTaskModal(task),
      labelMode: state.labelMode,
      buffer: state.buffer,
    });
    Gantt.render(wrap, state.currentSchedule, state.tasks);
  }

  // ---------- Schedule modal ----------
  $('#new-schedule-btn').addEventListener('click', () => {
    $('#sched-name').value = '';
    $('#sched-mode').value = 'day';
    $('#sched-start').value = new Date().toISOString().slice(0, 10);
    openModal('schedule-modal');
    setTimeout(() => $('#sched-name').focus(), 50);
  });

  $('#sched-save').addEventListener('click', async () => {
    const name = $('#sched-name').value.trim();
    if (!name) { toast('Name is required', true); return; }
    try {
      const s = await API.createSchedule({
        name,
        mode: $('#sched-mode').value,
        start_date: $('#sched-start').value,
      });
      closeModal('schedule-modal');
      await loadSchedules();
      selectSchedule(s.id);
    } catch (e) { toast(e.message, true); }
  });

  // ---------- Show labels toggle ----------
  $('#label-mode').addEventListener('change', (e) => {
    state.labelMode = e.target.value;
    if (state.currentSchedule) renderGantt();
  });

  // ---------- Buffer input ----------
  $('#buffer-units').addEventListener('input', (e) => {
    const v = parseInt(e.target.value, 10);
    state.buffer = isNaN(v) ? 0 : Math.max(0, v);
    if (state.currentSchedule) renderGantt();
  });

  // ---------- Window resize ----------
  let _resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(() => {
      if (state.currentSchedule) renderGantt();
    }, 100);
  });

  // ---------- Mode toggle ----------
  $$('#mode-toggle button').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!state.currentSchedule) return;
      const mode = btn.dataset.mode;
      if (state.currentSchedule.mode === mode) return;
      try {
        await API.updateSchedule(state.currentScheduleId, { mode });
        await selectSchedule(state.currentScheduleId);
      } catch (e) { toast(e.message, true); }
    });
  });

  // ---------- Task modal ----------
  $('#rename-schedule-btn').addEventListener('click', () => {
    if (!state.currentSchedule) return;
    renameSchedule(state.currentSchedule);
  });

  $('#add-task-btn').addEventListener('click', () => openTaskModal(null));

  function openTaskModal(task) {
    state.editingTask = task;
    const isEdit = !!task;
    const isWeek = state.currentSchedule.mode === 'week';
    const step = isWeek ? 0.5 : 1;
    $('#task-modal-title').textContent = isEdit ? 'Edit Task' : 'New Task';
    $('#task-name').value = task ? task.name : '';
    $('#task-start').value = task ? task.start_offset : 0;
    $('#task-start').step = step;
    $('#task-start').min = 0;
    $('#task-duration').value = task ? task.duration : 1;
    $('#task-duration').step = step;
    $('#task-duration').min = step;
    $('#task-progress').value = task ? Math.round((task.progress || 0) * 100) : 0;
    $('#task-delete').style.display = isEdit ? '' : 'none';
    const unit = isWeek ? 'week' : 'day';
    const unitPlural = unit + 's';
    $$('.unit-label').forEach((el, i) => {
      el.textContent = i === 0 ? unit : unitPlural;
    });
    refreshPrereqUI();
    openModal('task-modal');
    setTimeout(() => $('#task-name').focus(), 50);
  }

  function refreshPrereqUI() {
    const sel = $('#task-prereq-select');
    sel.innerHTML = '';
    const editingId = state.editingTask ? state.editingTask.id : null;
    const currentDeps = state.editingTask
      ? new Set((state.editingTask.dependencies || []).map((d) => d.prerequisite_id))
      : new Set();
    state.tasks.forEach((t) => {
      if (t.id === editingId) return;
      if (currentDeps.has(t.id)) return;
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.name;
      sel.appendChild(opt);
    });

    const list = $('#task-deps-list');
    list.innerHTML = '';
    if (!state.editingTask) return;
    (state.editingTask.dependencies || []).forEach((dep) => {
      const prereq = state.tasks.find((t) => t.id === dep.prerequisite_id);
      if (!prereq) return;
      const li = document.createElement('li');
      li.innerHTML = `<span>${escapeHtml(prereq.name)}</span>
                      <button class="remove" title="Remove">×</button>`;
      li.querySelector('.remove').addEventListener('click', async () => {
        try {
          await API.deleteDependency(dep.id);
          state.editingTask.dependencies = state.editingTask.dependencies.filter(
            (d) => d.id !== dep.id
          );
          refreshPrereqUI();
        } catch (e) { toast(e.message, true); }
      });
      list.appendChild(li);
    });
  }

  $('#task-prereq-add').addEventListener('click', async () => {
    if (!state.editingTask) {
      toast('Save the task first to add prerequisites', true);
      return;
    }
    const sel = $('#task-prereq-select');
    if (!sel.value) return;
    try {
      const dep = await API.addDependency(state.editingTask.id, parseInt(sel.value, 10));
      state.editingTask.dependencies = state.editingTask.dependencies || [];
      state.editingTask.dependencies.push(dep);
      refreshPrereqUI();
    } catch (e) { toast(e.message, true); }
  });

  $('#task-save').addEventListener('click', async () => {
    const isWeek = state.currentSchedule.mode === 'week';
    const step = isWeek ? 0.5 : 1;
    const snap = (v) => Math.round(v / step) * step;
    const payload = {
      name: $('#task-name').value.trim(),
      start_offset: Math.max(0, snap(parseFloat($('#task-start').value) || 0)),
      duration: Math.max(step, snap(parseFloat($('#task-duration').value) || step)),
      progress: Math.min(1, Math.max(0, (parseFloat($('#task-progress').value) || 0) / 100)),
    };
    if (!payload.name) { toast('Name is required', true); return; }
    try {
      if (state.editingTask) {
        await API.updateTask(state.editingTask.id, payload);
      } else {
        await API.createTask(state.currentScheduleId, payload);
      }
      closeModal('task-modal');
      await selectSchedule(state.currentScheduleId);
    } catch (e) { toast(e.message, true); }
  });

  $('#task-delete').addEventListener('click', async () => {
    if (!state.editingTask) return;
    if (!confirm(`Delete task "${state.editingTask.name}"?`)) return;
    try {
      await API.deleteTask(state.editingTask.id);
      closeModal('task-modal');
      await selectSchedule(state.currentScheduleId);
    } catch (e) { toast(e.message, true); }
  });

  // ---------- Utils ----------
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  // ---------- Boot ----------
  window.addEventListener('DOMContentLoaded', () => {
    sendSessionHeartbeat();
    setInterval(sendSessionHeartbeat, 10000);
    loadSchedules().catch((e) => toast(e.message, true));
  });

  window.addEventListener('pagehide', sendSessionClose);
  window.addEventListener('beforeunload', sendSessionClose);
})();
