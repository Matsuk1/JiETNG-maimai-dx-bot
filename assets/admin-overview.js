/* Overview tab: status, KPIs, 30-day trend and the per-day activity report. */
(function () {
  const POLL_MS = 30000;
  const QUEUE_WARN_RATIO = 0.75;
  const BREAKDOWN_VISIBLE = 8;

  const commandLabels = {
    // 新版命令路由（cmd.name，snake_case）
    'b_records': 'B-Records',
    'song_info': 'Song Info', 'plate': 'Plate',
    'version_songs': 'Version Songs', 'level_rank_list': 'Level / Constant List',
    'level_rank_progress': 'Level + Rank Progress',
    'level_records': 'Level Records', 'random_song': 'Random Song',
    // web async tasks + API 端点
    'song-record': 'Song Record', 'song-record-id': 'Song Record (ID)',
    'friend-rcd': 'Friend Record', 'song-info': 'Song Info (API)',
    'progress': 'Progress (API)', 'level-list': 'Level List (API)',
    // 历史数据（重构前事件，可能仍在 DB）
    'b50': 'Best 50 (legacy)', 'b40': 'Best 40 (legacy)',
    'b35': 'Best 35 (legacy)', 'b15': 'Best 15 (legacy)',
    'ab35': 'All Best 35 (legacy)', 'ab50': 'All Best 50 (legacy)',
    'apb50': 'AP Best 50 (legacy)', 'fdxb50': 'FDX Best 50 (legacy)',
    'rct50': 'Recent 50 (legacy)', 'idealb50': 'Ideal Best 50 (legacy)',
    'unknown': 'Unknown (legacy)', 'random': 'Random Song (legacy)',
    'version-list': 'Version List (legacy)', 'record-list': 'Record List (legacy)'
  };

  const $ = id => document.getElementById(id);
  const fmt = value => Number(value || 0).toLocaleString('en-US');
  const clampPct = value => Math.max(0, Math.min(100, Number(value) || 0));
  const setText = (id, value) => { const node = $(id); if (node) node.textContent = value; };
  const pct = (part, total) => (total ? part / total * 100 : 0);

  let latest = null;
  let selectedDate = null;
  let dayRequest = 0;
  let pollTimer = null;
  let hoverIndex = null;

  function serverToday() {
    const series = latest?.dau_30d || [];
    if (series.length) return series[series.length - 1].full_date;
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }

  /* ---- status ---- */
  function collectIssues(s) {
    const issues = [];
    const add = (level, text) => issues.push({level, text});
    if (s.business_stats_ok === false) {
      add('critical', s.business_stats_at
        ? `Statistics database unavailable; activity data is from ${s.business_stats_at}`
        : 'Statistics database unavailable; activity numbers read zero');
    }
    if (s.cpu_percent >= 85) add('warning', `CPU ${s.cpu_percent}%`);
    if (s.memory_percent >= 85) add('warning', `Memory ${s.memory_percent}%`);
    const max = Number(s.max_queue_size) || 0;
    [['Image', s.image_queue_size], ['Image query', s.image_query_queue_size], ['Web', s.web_queue_size]].forEach(([name, size]) => {
      if (!max) return;
      if (size >= max) add('critical', `${name} queue full (${size}/${max})`);
      else if (size / max >= QUEUE_WARN_RATIO) add('warning', `${name} queue ${size}/${max}`);
    });
    if (s.today_sync_total >= 10 && s.sync_success_rate < 90) {
      add('warning', `Sync success ${s.sync_success_rate}% today`);
    }
    const rate = taskRate(s);
    if (s.total_tasks_processed >= 20 && rate < 95) add('warning', `Task success ${rate.toFixed(1)}%`);
    return issues;
  }

  function setSignal(level, title, detail) {
    const signal = $('overview-signal');
    signal.classList.toggle('is-warning', level === 'warning');
    signal.classList.toggle('is-critical', level === 'critical');
    setText('overview-signal-title', title);
    setText('overview-signal-detail', detail);
  }

  function renderSignal(s) {
    const issues = collectIssues(s);
    if (!issues.length) {
      setSignal('ok', 'All systems operational', 'Resources, queues, syncs and tasks are within their operating range.');
      return;
    }
    const critical = issues.some(issue => issue.level === 'critical');
    setSignal(critical ? 'critical' : 'warning',
      critical ? 'Service needs attention' : 'Runtime pressure detected',
      issues.map(issue => issue.text).join(' · '));
  }

  function setConnection(state) {
    const labels = {live: ['Live', 'Service online'], stale: ['Stale', 'Connection lost'], expired: ['Signed out', 'Session expired']};
    document.body.dataset.overviewConnection = state;
    setText('overview-live-label', labels[state][0]);
    setText('sidebar-status', labels[state][1]);
  }

  /* ---- KPIs and runtime ---- */
  function taskRate(s) {
    const done = Number(s.total_tasks_processed) || 0;
    const ok = Math.max(0, done - s.total_tasks_failed - s.total_tasks_timed_out);
    return done ? ok / done * 100 : 100;
  }

  function toneBar(fill, percent, warnAt, criticalAt) {
    if (!fill) return;
    fill.style.width = clampPct(percent) + '%';
    fill.classList.toggle('is-warning', percent >= warnAt && percent < criticalAt);
    fill.classList.toggle('is-critical', percent >= criticalAt);
  }

  function renderKpis(s) {
    setText('overview-total-users', fmt(s.total_users));
    setText('overview-user-delta', `+${fmt(s.today_new_users)} today`);
    setText('overview-user-regions', `JP ${fmt(s.jp_users)} · INTL ${fmt(s.intl_users)}`);
    setText('overview-dau', fmt(s.dau));
    setText('overview-dau-note', `${fmt(s.dau_same_time_yesterday)} by now yesterday`);
    setText('overview-wau', fmt(s.wau));
    setText('overview-wau-note', `${pct(s.wau, s.total_users).toFixed(1)}% of users`);
    setText('overview-mau', fmt(s.mau));
    setText('overview-stickiness', `DAU/MAU ${s.stickiness}%`);

    const hasSync = s.today_sync_total > 0;
    setText('overview-sync', hasSync ? `${s.sync_success_rate}%` : '—');
    setText('overview-sync-note', hasSync ? `${fmt(s.today_sync_success)} of ${fmt(s.today_sync_total)} runs today` : 'No sync runs today');
    $('overview-sync').classList.toggle('is-warning', hasSync && s.sync_success_rate < 90);

    const rate = taskRate(s);
    setText('summary-task-success', `${rate.toFixed(1)}%`);
    setText('summary-task-note', `${fmt(s.total_tasks_failed)} failed · ${fmt(s.total_tasks_timed_out)} timed out`);
    $('summary-task-success').classList.toggle('is-warning', rate < 95);
  }

  function renderRuntime(s) {
    setText('overview-cpu', `${s.cpu_percent}%`);
    toneBar($('overview-cpu-fill'), s.cpu_percent, 85, 95);
    setText('overview-memory', `${s.memory_used_gb}/${s.total_memory} GB`);
    toneBar($('overview-memory-fill'), s.memory_percent, 85, 95);
    for (const component of s.memory_components || []) {
      const row = Array.from(document.querySelectorAll('[data-memory-component]'))
        .find(element => element.dataset.memoryComponent === component.key);
      if (!row) continue;
      row.querySelector('.health-value').textContent = component.memory_mb == null ? 'N/A' : `${component.memory_mb} MiB`;
      row.querySelector('.health-fill').style.width = clampPct(component.percent) + '%';
    }
    const max = Number(s.max_queue_size) || 0;
    [['image', s.image_queue_size], ['image-query', s.image_query_queue_size], ['web', s.web_queue_size]].forEach(([key, size]) => {
      setText(`overview-${key}-queue`, `${fmt(size)}/${fmt(max)}`);
      toneBar($(`overview-${key}-queue-fill`), pct(size, max), QUEUE_WARN_RATIO * 100, 100);
    });
    const queued = s.image_queue_size + s.image_query_queue_size + s.web_queue_size;
    setText('summary-queue-backlog', `${fmt(queued)} queued · ${fmt(s.running_tasks)} running`
      + (s.running_tasks ? ` · longest ${fmt(s.longest_running_seconds)}s` : ''));
    const failure = s.last_task_failure;
    $('overview-last-failure').hidden = !failure;
    if (failure) {
      setText('overview-last-failure-meta', `${failure.function || 'Task'} · ${String(failure.finished_at || '').slice(11)}`);
      setText('overview-last-failure-error', failure.error);
    }
    setText('summary-uptime', s.uptime);
    setText('sidebar-uptime', `${s.uptime} uptime`);
    setText('summary-process-memory', `${fmt(s.process_memory_mb)} MB`);
    setText('summary-threads', fmt(s.thread_count));
    setText('stat-event-dropped', fmt(s.event_dropped));
    $('stat-event-dropped').classList.toggle('is-warning', s.event_dropped > 0);
    $('stat-event-dropped').title = s.event_last_error ? `Last write error: ${s.event_last_error}` : '';
    setText('summary-runtime', `Python ${s.python_version}`);
    setText('summary-host', `${s.hostname}:${s.port}`);
    const updated = $('overview-updated');
    updated.textContent = `Updated ${String(s.timestamp).slice(11)}`;
    updated.title = `Runtime ${s.timestamp} · business metrics ${s.business_stats_at || 'unknown'}`;
  }

  /* ---- 30-day trend ---- */
  function niceTicks(maxValue) {
    const raw = Math.max(1, maxValue) / 4;
    const power = 10 ** Math.floor(Math.log10(raw));
    const ratio = raw / power;
    const step = Math.max(1, (ratio <= 1 ? 1 : ratio <= 2 ? 2 : ratio <= 5 ? 5 : 10) * power);
    const ticks = [];
    for (let tick = 0; tick < maxValue + step; tick += step) ticks.push(tick);
    return ticks;
  }

  function renderTrend() {
    const host = $('dau-chart');
    const series = latest?.dau_30d || [];
    const width = host.clientWidth;
    if (!width) return;
    if (!series.length) {
      host.innerHTML = '<div class="overview-empty">No activity recorded yet</div>';
      setText('overview-trend-summary', 'Last 30 days');
      return;
    }
    const values = series.map(point => point.dau);
    const peak = Math.max(...values);
    const average = Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
    setText('overview-trend-summary', `Last 30 days · peak ${fmt(peak)} · avg ${fmt(average)}`);

    const height = width < 480 ? 180 : 300;
    const box = {left: 38, right: 10, top: 10, bottom: 26};
    const plotW = width - box.left - box.right;
    const plotH = height - box.top - box.bottom;
    const ticks = niceTicks(peak);
    const top = ticks[ticks.length - 1];
    const x = index => box.left + (series.length > 1 ? index * plotW / (series.length - 1) : plotW / 2);
    const y = value => box.top + plotH - value / top * plotH;
    const line = series.map((point, index) => `${x(index).toFixed(1)},${y(point.dau).toFixed(1)}`).join(' ');
    const area = `${x(0).toFixed(1)},${box.top + plotH} ${line} ${x(series.length - 1).toFixed(1)},${box.top + plotH}`;
    const grid = ticks.map(tick => `
      <line class="chart-grid" x1="${box.left}" x2="${width - box.right}" y1="${y(tick)}" y2="${y(tick)}"></line>
      <text class="chart-label" x="${box.left - 8}" y="${y(tick) + 4}" text-anchor="end">${fmt(tick)}</text>`).join('');
    const labelCount = width < 480 ? 4 : 6;
    const labelEvery = Math.max(1, Math.ceil((series.length - 1) / (labelCount - 1)));
    const labels = series.map((point, index) => {
      const lastIndex = series.length - 1;
      const show = index === lastIndex || (index % labelEvery === 0 && lastIndex - index >= labelEvery / 2);
      if (!show) return '';
      const anchor = index === 0 ? 'start' : index === lastIndex ? 'end' : 'middle';
      return `<text class="chart-label" x="${x(index)}" y="${height - 6}" text-anchor="${anchor}">${escapeHtml(point.date)}</text>`;
    }).join('');
    const selected = selectedDate ? series.findIndex(point => point.full_date === selectedDate) : series.length - 1;
    const marker = selected >= 0
      ? `<circle class="chart-selected" cx="${x(selected)}" cy="${y(series[selected].dau)}" r="4"></circle>` : '';
    host.innerHTML = `
      <svg width="${width}" height="${height}" role="img" aria-label="Daily active users over the last 30 days, peak ${peak}, average ${average}">
        ${grid}
        <polygon class="chart-area" points="${area}"></polygon>
        <polyline class="chart-line" points="${line}"></polyline>
        <line class="chart-cursor" id="dau-cursor" y1="${box.top}" y2="${box.top + plotH}" style="display:none"></line>
        ${marker}
        ${labels}
      </svg>`;

    const tooltip = $('dau-tooltip');
    const svg = host.querySelector('svg');
    const cursor = $('dau-cursor');
    const nearest = event => {
      const rect = svg.getBoundingClientRect();
      const ratio = (event.clientX - rect.left - box.left) / plotW;
      return Math.max(0, Math.min(series.length - 1, Math.round(ratio * (series.length - 1))));
    };
    svg.addEventListener('pointermove', event => {
      hoverIndex = nearest(event);
      const point = series[hoverIndex];
      tooltip.textContent = `${point.date} · DAU ${fmt(point.dau)} · +${fmt(point.new_users)} new`;
      tooltip.hidden = false;
      const left = x(hoverIndex) - tooltip.offsetWidth / 2;
      tooltip.style.left = `${Math.max(0, Math.min(left, width - tooltip.offsetWidth))}px`;
      tooltip.style.top = `${Math.max(0, y(point.dau) - tooltip.offsetHeight - 10)}px`;
      cursor.setAttribute('x1', x(hoverIndex));
      cursor.setAttribute('x2', x(hoverIndex));
      cursor.style.display = '';
    });
    svg.addEventListener('pointerleave', () => { tooltip.hidden = true; cursor.style.display = 'none'; });
    svg.addEventListener('click', event => selectDate(series[nearest(event)].full_date));
  }

  /* ---- per-day report ---- */
  function renderHourly(hourly) {
    const host = $('hourly-chart');
    const hours = Array.from({length: 24}, (_, hour) => Number(hourly?.[hour]) || 0);
    const peak = Math.max(...hours);
    if (!peak) {
      host.innerHTML = '<div class="overview-empty">No events in this day</div>';
      setText('hourly-summary', 'Events by hour');
      return;
    }
    const peakHour = hours.indexOf(peak);
    setText('hourly-summary', `Peak ${String(peakHour).padStart(2, '0')}:00 · ${fmt(peak)}`);
    host.innerHTML = `
      <div class="hourly-bars" role="img" aria-label="Events by hour, peak ${peak} at ${peakHour}:00">
        ${hours.map((value, hour) => `<span class="hourly-bar${hour === peakHour ? ' is-peak' : ''}" title="${String(hour).padStart(2, '0')}:00 · ${fmt(value)}"><i style="height:${value ? Math.max(3, value / peak * 100) : 0}%"></i></span>`).join('')}
      </div>
      <div class="hourly-axis"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>`;
  }

  function breakdownRow(row, maxCount, total) {
    const label = commandLabels[row.command] || row.command;
    return `<div class="command-row">
      <div class="command-name" title="${escapeHtml(row.command)}">${escapeHtml(label)}</div>
      <div class="command-bar"><span style="width:${clampPct(row.count / maxCount * 100)}%"></span></div>
      <div class="command-count">${fmt(row.count)}<small>${Math.round(pct(row.count, total))}%</small></div>
    </div>`;
  }

  function renderBreakdown(rows) {
    const host = $('breakdown-chart');
    if (!rows?.length) {
      host.innerHTML = '<div class="overview-empty">No image commands in this day</div>';
      return;
    }
    const total = rows.reduce((sum, row) => sum + row.count, 0);
    const maxCount = rows[0].count || 1;
    const render = list => list.map(row => breakdownRow(row, maxCount, total)).join('');
    const rest = rows.slice(BREAKDOWN_VISIBLE);
    host.innerHTML = render(rows.slice(0, BREAKDOWN_VISIBLE)) + (rest.length
      ? `<details class="command-more"><summary>Show ${rest.length} more</summary>${render(rest)}</details>` : '');
  }

  function renderSyncFailures(failures) {
    const host = $('sync-failures');
    host.hidden = !failures?.length;
    $('sync-failure-list').innerHTML = (failures || []).map(failure => `<li>
      <span class="sync-failure-count">${fmt(failure.count)}</span>
      <span class="sync-failure-reason">${escapeHtml(failure.reason)}</span>
    </li>`).join('');
  }

  function renderDay(day, date) {
    const isToday = date === serverToday();
    setText('activity-title', isToday ? "Today's Activity" : `${date} Activity`);
    $('overview-today-btn').hidden = isToday;
    const input = $('hourly-date');
    input.value = date;
    input.max = serverToday();
    setText('stat-image-calls', fmt(day.image_calls));
    setText('stat-webhook-msgs', fmt(day.webhook_msgs));
    setText('stat-sync', `${fmt(day.sync_success)} / ${fmt(day.sync_total)}`);
    setText('stat-sync-rate', day.sync_total ? `${day.sync_success_rate}% success` : 'No runs');
    setText('stat-bindings', fmt(day.bindings));
    setText('stat-unbinds', `${fmt(day.unbinds)} unbinds`);
    setText('stat-record-exports', fmt(day.record_exports));
    setText('stat-record-imports', fmt(day.record_imports));
    renderHourly(day.hourly);
    renderBreakdown(day.image_command_breakdown);
    renderSyncFailures(day.sync_failures);
  }

  function todayReport(s) {
    return {
      image_calls: s.today_image_calls, webhook_msgs: s.today_webhook_msgs,
      sync_success: s.today_sync_success, sync_total: s.today_sync_total, sync_success_rate: s.sync_success_rate,
      bindings: s.today_bindings, unbinds: s.today_unbinds,
      record_exports: s.today_record_exports, record_imports: s.today_record_imports,
      hourly: s.hourly_today, image_command_breakdown: s.image_command_breakdown,
      sync_failures: s.today_sync_failures,
    };
  }

  function selectDate(date) {
    const request = ++dayRequest;
    if (!date || date === serverToday()) {
      selectedDate = null;
      renderDay(todayReport(latest), serverToday());
      renderTrend();
      return;
    }
    selectedDate = date;
    renderTrend();
    fetch(`/admin/api/hourly?date=${encodeURIComponent(date)}`)
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(day => {
        if (day.ok === false) throw new Error('statistics database unavailable');
        if (request === dayRequest) renderDay(day, date);
      })
      .catch(error => { if (request === dayRequest) showToast(`Failed to load ${date}: ${error.message}`, 'error'); });
  }

  /* ---- data flow ---- */
  function applyStats(stats) {
    latest = stats;
    setConnection('live');
    renderSignal(stats);
    renderKpis(stats);
    renderRuntime(stats);
    renderTrend();
    if (!selectedDate) renderDay(todayReport(stats), serverToday());
  }

  function loadOverview(force) {
    const url = force ? `/admin/api/overview?refresh=${Date.now()}` : '/admin/api/overview';
    return fetch(url, {redirect: 'manual'}).then(response => {
      if (response.type === 'opaqueredirect' || response.status === 401 || response.status === 302) {
        const error = new Error('Session expired, please re-login');
        error.expired = true;
        throw error;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }).then(data => {
      if (!data.success) throw new Error(data.message || 'Refresh failed');
      applyStats(data.stats);
    }).catch(error => {
      if (error.expired) {
        clearInterval(pollTimer);
        setConnection('expired');
        setSignal('critical', 'Session expired', 'Sign in again to resume live monitoring.');
      } else {
        setConnection('stale');
        setSignal('critical', 'Cannot reach the server', `Showing data from ${latest?.timestamp || 'page load'}.`);
      }
      throw error;
    });
  }

  window.refreshStats = function (button) {
    button.disabled = true;
    button.classList.add('is-loading');
    button.setAttribute('aria-busy', 'true');
    loadOverview(true)
      .then(() => showToast('Stats refreshed', 'success'))
      .catch(error => showToast(error.message, 'error'))
      .finally(() => {
        button.disabled = false;
        button.classList.remove('is-loading');
        button.removeAttribute('aria-busy');
      });
  };

  function poll() {
    if (!document.hidden) loadOverview(false).catch(() => {});
  }

  latest = JSON.parse($('overview-initial-stats').textContent);
  applyStats(latest);
  $('hourly-date').addEventListener('change', event => selectDate(event.target.value));
  $('overview-today-btn').addEventListener('click', () => selectDate(null));
  new ResizeObserver(renderTrend).observe($('dau-chart'));
  pollTimer = setInterval(poll, POLL_MS);
  document.addEventListener('visibilitychange', poll);
})();
