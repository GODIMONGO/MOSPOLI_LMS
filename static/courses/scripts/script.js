// script.js (defensive, DOMContentLoaded wrapped)
document.addEventListener('DOMContentLoaded', () => {
  // Key for storage
  const TASKS_KEY = 'tm_v2_tasks';

  // small helpers
  const qs = s => document.querySelector(s);
  const qsa = s => Array.from(document.querySelectorAll(s));
  const uid = () => '_' + Math.random().toString(36).slice(2, 9);
  const escapeHtml = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  // Grab DOM elements (guarded)
  const titleEl = qs('#title');
  const descEl = qs('#description');
  const dueEl = qs('#due');
  const priorityEl = qs('#priority');
  const progressEl = qs('#progress');
  const progressValEl = qs('#progress-val');
  const saveBtn = qs('#save-btn');
  const clearBtn = qs('#clear-btn');
  const taskListEl = qs('#task-list');
  const overallCircle = qs('#overall-circle');
  const overallPercent = qs('#overall-percent');
  const totalCountEl = qs('#total-count');
  const completedCountEl = qs('#completed-count');
  const avgProgressEl = qs('#avg-progress');
  const searchEl = qs('#search');
  const sortEl = qs('#sort');
  const filterPriority = qs('#filter-priority');
  const exportBtn = qs('#export-btn');
  const importBtn = qs('#import-btn');
  const importFile = qs('#import-file');
  const clearAllBtn = qs('#clear-all');

  // Verify required DOM nodes - if something missing, log and exit gracefully
  const required = [
    ['title', titleEl],
    ['save-btn', saveBtn],
    ['task-list', taskListEl],
    ['overall-circle', overallCircle],
    ['overall-percent', overallPercent]
  ];
  for (const [name, el] of required) {
    if (!el) console.warn(`Warning: element with id "${name}" not found in DOM. Some features may be disabled.`);
  }

  // Data
  let tasks = [];
  try {
    tasks = JSON.parse(localStorage.getItem(TASKS_KEY)) || [];
  } catch (e) {
    console.warn('Could not parse tasks from localStorage - resetting.', e);
    tasks = [];
  }
  let editId = null;

  // Event wiring with guards
  if (progressEl && progressValEl) {
    progressEl.addEventListener('input', () => { progressValEl.textContent = progressEl.value + '%'; });
  }
  if (saveBtn) saveBtn.addEventListener('click', onSave);
  if (clearBtn) clearBtn.addEventListener('click', onClear);
  if (searchEl) searchEl.addEventListener('input', render);
  if (sortEl) sortEl.addEventListener('change', render);
  if (filterPriority) filterPriority.addEventListener('change', render);

  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      try {
        const data = JSON.stringify(tasks, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tasks.json';
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) { console.error('Export failed', err); }
    });
  }

  if (importBtn && importFile) {
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const r = new FileReader();
      r.onload = ev => {
        try {
          const imported = JSON.parse(ev.target.result);
          if (Array.isArray(imported)) {
            imported.forEach(it => { if (!it.id) it.id = uid(); });
            tasks = imported.concat(tasks);
            saveAndRender();
            alert('Imported ' + imported.length + ' tasks');
          } else alert('Invalid file format - expected JSON array');
        } catch (err) {
          alert('Error parsing file');
          console.error(err);
        }
      };
      r.readAsText(f);
      // reset input so same file can be imported again if needed
      importFile.value = '';
    });
  }

  if (clearAllBtn) {
    clearAllBtn.addEventListener('click', () => {
      if (confirm('Delete all tasks?')) { tasks = []; saveAndRender(); }
    });
  }

  // CRUD helpers
  function onSave() {
    if (!titleEl) return alert('UI not ready (missing title input)');
    const title = titleEl.value.trim();
    if (!title) { alert('Enter a title'); return; }
    const data = {
      title,
      description: descEl ? descEl.value.trim() : '',
      due: dueEl ? dueEl.value : '',
      priority: priorityEl ? priorityEl.value : 'Medium',
      progress: progressEl ? Number(progressEl.value) : 0,
      completed: progressEl ? Number(progressEl.value) >= 100 : false,
      created: Date.now()
    };
    if (editId) {
      const idx = tasks.findIndex(t => t.id === editId);
      if (idx > -1) tasks[idx] = { ...tasks[idx], ...data };
      editId = null;
      if (saveBtn) saveBtn.textContent = 'Add Task';
    } else {
      tasks.unshift({ id: uid(), ...data });
    }
    onClear();
    saveAndRender();
  }

  function onClear() {
    if (titleEl) titleEl.value = '';
    if (descEl) descEl.value = '';
    if (dueEl) dueEl.value = '';
    if (priorityEl) priorityEl.value = 'Medium';
    if (progressEl) progressEl.value = 0;
    if (progressValEl) progressValEl.textContent = '0%';
    editId = null;
    if (saveBtn) saveBtn.textContent = 'Add Task';
  }

  function editTask(id) {
    const t = tasks.find(x => x.id === id);
    if (!t) return;
    if (titleEl) titleEl.value = t.title;
    if (descEl) descEl.value = t.description || '';
    if (dueEl) dueEl.value = t.due || '';
    if (priorityEl) priorityEl.value = t.priority || 'Medium';
    if (progressEl) progressEl.value = t.progress || 0;
    if (progressValEl) progressValEl.textContent = (t.progress || 0) + '%';
    editId = id;
    if (saveBtn) saveBtn.textContent = 'Update Task';
    // scroll to top for convenience
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function toggleComplete(id, checked) {
    const idx = tasks.findIndex(t => t.id === id);
    if (idx > -1) {
      tasks[idx].completed = !!checked;
      if (checked) tasks[idx].progress = 100;
      saveAndRender();
    }
  }

  function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    tasks = tasks.filter(t => t.id !== id);
    saveAndRender();
  }

  // drag & drop
  let dragSrc = null;
  function dragStart(e) {
    dragSrc = this;
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', this.dataset.id); } catch (err) { /* ignore */ }
    this.style.opacity = '0.6';
  }
  function dragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }
  function dropItem(e) {
    e.stopPropagation();
    const srcId = dragSrc && dragSrc.dataset && dragSrc.dataset.id;
    const dstId = this && this.dataset && this.dataset.id;
    if (!srcId || !dstId || srcId === dstId) return;
    const sIdx = tasks.findIndex(t => t.id === srcId);
    const dIdx = tasks.findIndex(t => t.id === dstId);
    if (sIdx === -1 || dIdx === -1) return;
    const item = tasks.splice(sIdx, 1)[0];
    tasks.splice(dIdx, 0, item);
    saveAndRender();
  }
  function dragEnd() { this.style.opacity = '1'; }

  // render list
  function render() {
    if (!taskListEl) return;
    const q = searchEl ? searchEl.value.trim().toLowerCase() : '';
    let list = [...tasks];

    // priority filter
    const fp = filterPriority ? filterPriority.value : 'All';
    if (fp !== 'All') list = list.filter(t => t.priority === fp);

    // search
    if (q) list = list.filter(t => (t.title + ' ' + (t.description || '')).toLowerCase().includes(q));

    // sort
    const s = sortEl ? sortEl.value : 'created';
    if (s === 'due') list.sort((a, b) => (a.due || '').localeCompare(b.due || ''));
    else if (s === 'priority') list.sort((a, b) => priorityRank(b.priority) - priorityRank(a.priority));
    else if (s === 'progress') list.sort((a, b) => b.progress - a.progress);
    else list.sort((a, b) => b.created - a.created);

    taskListEl.innerHTML = '';
    list.forEach(t => {
      const li = document.createElement('li');
      li.className = 'task' + (t.completed ? ' completed' : '');
      li.setAttribute('draggable', 'true');
      li.dataset.id = t.id;

      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.innerHTML = `<div class="title"><h3>${escapeHtml(t.title)}</h3></div>
        <p class="desc">${escapeHtml(t.description || '')}</p>
        <div class="tag">${escapeHtml(t.priority)} priority ${t.due ? ' • due ' + escapeHtml(t.due) : ''}</div>`;

      const right = document.createElement('div');
      right.className = 'right';

      const range = document.createElement('input');
      range.type = 'range'; range.min = 0; range.max = 100; range.value = t.progress || 0; range.className = 'small-range';
      range.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        const idx = tasks.findIndex(x => x.id === t.id);
        if (idx > -1) {
          tasks[idx].progress = val;
          tasks[idx].completed = val >= 100;
          render(); // re-render to update stats and UI
        }
      });

      const chk = document.createElement('input');
      chk.type = 'checkbox'; chk.className = 'checkbox'; chk.checked = !!t.completed;
      chk.addEventListener('change', () => toggleComplete(t.id, chk.checked));

      const editBtn = document.createElement('button'); editBtn.className = 'small-btn'; editBtn.textContent = 'Edit';
      editBtn.addEventListener('click', () => editTask(t.id));

      const delBtn = document.createElement('button'); delBtn.className = 'small-btn'; delBtn.textContent = 'Delete';
      delBtn.addEventListener('click', () => deleteTask(t.id));

      right.appendChild(range); right.appendChild(chk); right.appendChild(editBtn); right.appendChild(delBtn);

      li.appendChild(meta); li.appendChild(right);

      // drag handlers (guard attach)
      li.addEventListener('dragstart', dragStart);
      li.addEventListener('dragover', dragOver);
      li.addEventListener('drop', dropItem);
      li.addEventListener('dragend', dragEnd);

      taskListEl.appendChild(li);
    });

    updateStats();
  }

  // stats and ring
  function updateStats() {
    const total = tasks.length;
    const completed = tasks.filter(t => t.completed || t.progress >= 100).length;
    const avg = total ? Math.round(tasks.reduce((s, t) => s + (Number(t.progress) || 0), 0) / total) : 0;

    if (totalCountEl) totalCountEl.textContent = total;
    if (completedCountEl) completedCountEl.textContent = completed;
    if (avgProgressEl) avgProgressEl.textContent = avg + '%';
    if (overallPercent) overallPercent.textContent = avg + '%';
    setRingPercent(avg);
  }

  function setRingPercent(pct) {
    if (!overallCircle) return;
    try {
      const r = overallCircle.r.baseVal.value;
      const c = 2 * Math.PI * r;
      overallCircle.style.strokeDasharray = c;
      const offset = c - (pct / 100) * c;
      overallCircle.style.strokeDashoffset = offset;
    } catch (err) {
      console.warn('Could not set ring percent', err);
    }
  }

  function priorityRank(p) { if (p === 'High') return 3; if (p === 'Medium') return 2; return 1; }

  function saveAndRender() {
    try { localStorage.setItem(TASKS_KEY, JSON.stringify(tasks)); } catch (err) { console.warn('Failed to write to localStorage', err); }
    render();
  }

  // initial boot - seed sample if empty
  (function boot() {
    try {
      // ensure circle initial value
      if (overallCircle) {
        const r = overallCircle.r.baseVal.value;
        overallCircle.style.strokeDasharray = 2 * Math.PI * r;
        overallCircle.style.strokeDashoffset = 2 * Math.PI * r;
      }
      if (tasks.length === 0) {
        tasks = [
          { id: uid(), title: 'Finish assignment', description: 'Important', due: '', priority: 'High', progress: 0, completed: false, created: Date.now() - 2000000 }
        ];
        saveAndRender();
      } else render();
    } catch (err) {
      console.error('Boot failed', err);
    }
  })();

});
