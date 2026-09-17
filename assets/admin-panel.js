    const languageOptions = window.JIETNG_ADMIN_CONFIG.languageOptions;
    const defaultLanguage = window.JIETNG_ADMIN_CONFIG.defaultLanguage;

    function localizedValues(selector) {
      return Object.fromEntries(
        [...document.querySelectorAll(selector)].map(input => [input.dataset.language, input.value.trim()])
      );
    }

    function setLocalizedValues(selector, values = {}) {
      document.querySelectorAll(selector).forEach(input => {
        input.value = values[input.dataset.language] || '';
      });
    }

    function localizedRows(values = {}) {
      values ||= {};
      return languageOptions.map(({code, label}) => `
        <div class="list-item" style="align-items:flex-start;gap:12px;">
          <span style="color:var(--text-secondary);font-size:13px;white-space:nowrap;padding-top:1px;min-width:80px;">${escapeHtml(label)}</span>
          <span style="font-size:13px;color:var(--text-color);line-height:1.6;flex:1;">${escapeHtml(values[code] || '—')}</span>
        </div>`).join('');
    }

    const adminPageTitles = {
      stats: 'Overview',
      operations: 'Operations',
      users: 'Users',
      content: 'Content',
      maintenance: 'Maintenance'
    };

    const adminTabGroups = {
      stats: ['stats'],
      operations: ['operations'],
      users: ['users'],
      content: ['notices', 'tipad'],
      maintenance: ['dxdata', 'backups', 'backgrounds', 'devtoken']
    };

    function normalizeAdminTab(tabName) {
      if (tabName === 'logs' || tabName === 'notifications') return 'operations';
      if (['notices', 'tipad'].includes(tabName)) return 'content';
      if (['dxdata', 'backups', 'backgrounds', 'devtoken'].includes(tabName)) return 'maintenance';
      return tabName || 'stats';
    }

    function activateAdminTab(tabName, tabButton) {
      const panes = adminTabGroups[tabName] || [tabName];
      document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
      });
      document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
      });
      panes.forEach(pane => {
        document.getElementById(pane + '-tab')?.classList.add('active');
      });
      const activeButton = tabButton || document.querySelector('.tab[data-tab="' + tabName + '"]');
      if (activeButton) activeButton.classList.add('active');
      const pageTitle = document.getElementById('admin-page-title');
      if (pageTitle) pageTitle.textContent = adminPageTitles[tabName] || 'Admin Console';
    }

    function loadAdminTabData(tabName) {
      if (tabName === 'operations') {
        refreshNotifications();
        setTimeout(scrollLogsToBottom, 100);
      }
      if (tabName === 'content') {
        loadNotices();
        loadTipAds();
      }
      if (tabName === 'users') {
        loadUsers();
      }
      if (tabName === 'maintenance') {
        loadDXDataStatus();
        loadDXDataAudit();
        loadBackups();
        loadBackgrounds();
        loadDevTokens();
      }
    }

    function isMobileAdminLayout() {
      return window.matchMedia('(max-width: 768px)').matches;
    }

    function updateMobileTopbarOffset() {
      if (!isMobileAdminLayout()) {
        document.body.style.removeProperty('--mobile-nav-offset');
        return;
      }

      const sidebar = document.querySelector('.sidebar');
      const brand = document.querySelector('.brand-block');
      const collapsed = document.body.classList.contains('admin-mobile-nav-collapsed');
      const sidebarStyle = sidebar ? getComputedStyle(sidebar) : null;
      const sidebarChrome = sidebarStyle
        ? ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
            .reduce((total, property) => total + parseFloat(sidebarStyle[property] || 0), 0)
        : 0;
      const height = collapsed
        ? (brand ? brand.getBoundingClientRect().height + sidebarChrome : 62)
        : (sidebar ? sidebar.getBoundingClientRect().height : 64);
      document.body.style.setProperty('--mobile-nav-offset', height + 'px');
    }

    function setMobileNavCollapsed(collapsed) {
      const nextCollapsed = isMobileAdminLayout() ? collapsed : false;
      document.body.classList.toggle('admin-mobile-nav-collapsed', nextCollapsed);
      const btn = document.getElementById('mobile-nav-toggle');
      if (btn) {
        btn.setAttribute('aria-expanded', nextCollapsed ? 'false' : 'true');
      }
      window.requestAnimationFrame(updateMobileTopbarOffset);
    }

    function toggleMobileNav() {
      setMobileNavCollapsed(!document.body.classList.contains('admin-mobile-nav-collapsed'));
    }

    function switchTab(tabName, tabButton) {
      tabName = normalizeAdminTab(tabName);
      activateAdminTab(tabName, tabButton);
      localStorage.setItem('admin_active_tab', tabName);
      if (isMobileAdminLayout()) {
        setMobileNavCollapsed(true);
      }
      loadAdminTabData(tabName);
    }

    // Restore tab on page load
    window.addEventListener('DOMContentLoaded', function() {
      setMobileNavCollapsed(isMobileAdminLayout());
      updateMobileTopbarOffset();
      document.getElementById('mobile-nav-content')?.addEventListener('transitionend', updateMobileTopbarOffset);

      // 从通知点击进入时，hash 为 #notifications，跳转到 Operations
      if (window.location.hash === '#notifications') {
        switchTab('operations');
        return;
      }

      const savedTab = normalizeAdminTab(localStorage.getItem('admin_active_tab'));
      if (savedTab && adminTabGroups[savedTab]) {
        activateAdminTab(savedTab);
        loadAdminTabData(savedTab);
      }

      // 转换日志中的 ANSI 颜色代码
      const logViewer = document.getElementById('log-viewer');
      if (logViewer && logViewer.textContent) {
        const logText = logViewer.textContent;
        setRawLogs(logText);
      }

      // 如果当前显示的是 Operations，滚动日志到底部
      if (document.getElementById('operations-tab')?.classList.contains('active')) {
        setTimeout(scrollLogsToBottom, 100);
      }
    });

    window.addEventListener('resize', function() {
      setMobileNavCollapsed(isMobileAdminLayout());
      updateMobileTopbarOffset();
    });

    function toggleUserData(userId) {
      const dataElement = document.getElementById('data-' + userId);
      const toggleIcon = document.getElementById('toggle-' + userId);

      if (dataElement.classList.contains('expanded')) {
        dataElement.classList.remove('expanded');
        toggleIcon.textContent = '▼';
      } else {
        dataElement.classList.add('expanded');
        toggleIcon.textContent = '▲';
      }
    }

    function triggerUpdate(userId) {
      if (confirm('Trigger maimai_update for user ' + userId + '?\n\nThe update will run in the background.')) {
        // 禁用按钮,显示加载状态
        const btn = event.target;
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Queuing...';

        fetch('/admin/trigger_update', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: userId})
        })
        .then(res => res.json())
        .then(data => {
          // 显示成功消息但不重载页面
          alert('✅ ' + (data.message || 'Update task queued successfully!\n\nThe update is running in the background.\nYou will receive a notification when it completes.'));

          // 恢复按钮
          btn.disabled = false;
          btn.textContent = originalText;
        })
        .catch(err => {
          alert('❌ Error: ' + err);
          btn.disabled = false;
          btn.textContent = originalText;
        });
      }
    }

    function refreshUserData(userId) {
      const btn = event.target;
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Loading...';

      fetch('/admin/get_user_data', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          // 更新 JSON 显示
          const jsonViewer = document.querySelector('#data-' + userId + ' .json-viewer pre');
          jsonViewer.textContent = data.json_str;

          // 更新昵称
          const nicknameElement = document.querySelector('[data-user-id="' + userId + '"] .user-nickname');
          nicknameElement.textContent = data.nickname;
          const userItem = document.querySelector('[data-user-id="' + userId + '"]');
          if (userItem) {
            userItem.setAttribute('data-nickname', data.nickname.toLowerCase());
          }

          // 显示成功消息
          showToast('✅ User data refreshed', 'success');
        } else {
          alert('❌ Error: ' + (data.message || 'Unknown error'));
        }

        btn.disabled = false;
        btn.textContent = originalText;
      })
      .catch(err => {
        alert('❌ Network error: ' + err);
        btn.disabled = false;
        btn.textContent = originalText;
      });
    }

    // Toast 通知
    let _toastOffset = 0;
    function showToast(message, type) {
      if (!type) type = message.startsWith('✗') ? 'error' : 'success';
      const borderColor = type === 'success' ? 'var(--success-color)'
                        : type === 'warning'  ? 'var(--warning-color)'
                        : 'var(--danger-color)';
      const textColor = borderColor;

      const toast = document.createElement('div');
      const offset = _toastOffset;
      _toastOffset += 56;
      toast.style.cssText = `
        position: fixed;
        bottom: ${24 + offset}px;
        right: 20px;
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 3px solid ${borderColor};
        color: ${textColor};
        padding: 10px 16px;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        font-size: 13px;
        font-weight: 600;
        max-width: 280px;
        line-height: 1.5;
        animation: toastIn 0.25s ease;
      `;
      toast.textContent = message;
      document.body.appendChild(toast);

      setTimeout(() => {
        toast.style.animation = 'toastOut 0.25s ease forwards';
        setTimeout(() => {
          toast.remove();
          _toastOffset = Math.max(0, _toastOffset - 56);
        }, 250);
      }, 3000);
    }

    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
      @keyframes toastIn {
        from { transform: translateX(60px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes toastOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(60px); opacity: 0; }
      }
    `;
    document.head.appendChild(style);

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
      const modal = document.getElementById('editUserModal');
      if (event.target === modal) {
        closeEditModal();
      }
    });

    function deleteUser(userId) {
      if (confirm('⚠️ Are you sure you want to delete this user?\n\nUser ID: ' + userId + '\n\nThis action CANNOT be undone!')) {
        const button = event.target;
        button.disabled = true;
        button.textContent = 'Deleting...';

        fetch('/admin/delete_user', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: userId})
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast('✓ User deleted successfully');
            // 移除用户元素
            const userElement = document.querySelector('[data-user-id="' + userId + '"]');
            if (userElement) {
              userElement.style.opacity = '0';
              userElement.style.transition = 'opacity 0.3s';
              setTimeout(() => userElement.remove(), 300);
            }
          } else {
            showToast('✗ ' + (data.message || 'Failed to delete user'));
            button.disabled = false;
            button.textContent = 'Delete';
          }
        })
        .catch(err => {
          showToast('✗ Error: ' + err);
          button.disabled = false;
          button.textContent = 'Delete';
        });
      }
    }

    let _usersLoading = false;
    let _usersOffset = 0;
    let _usersHasMore = false;
    let _usersSearchTimer = null;
    const USERS_PAGE_SIZE = 50;

    function userCardHtml(user) {
      const userId = escapeHtml(user.user_id);
      const nickname = escapeHtml(user.nickname || '');
      return `
        <div class="user-item" data-user-id="${userId}" data-nickname="${nickname.toLowerCase()}">
          <div class="list-item user-header" onclick="toggleUserData('${userId}')">
            <div class="list-item-info">
              <span class="list-item-label" style="font-family: 'Courier New', monospace; color: var(--accent-color);">${userId}</span>
              <span class="list-item-meta user-nickname" style="font-family: inherit;">${nickname}</span>
            </div>
            <div class="user-actions" onclick="event.stopPropagation()">
              <button class="btn btn-primary" onclick="triggerUpdate('${userId}')">Update</button>
              <button class="btn btn-success" onclick="refreshUserData('${userId}')">Refresh</button>
              <button class="btn btn-warning" onclick="editUser('${userId}')">Edit</button>
              <button class="btn btn-danger" onclick="deleteUser('${userId}')">Delete</button>
              <span class="toggle-icon" id="toggle-${userId}">▼</span>
            </div>
          </div>
          <div class="user-data" id="data-${userId}">
            <div class="json-viewer"><pre>${escapeHtml(user.json_str || '{}')}</pre></div>
          </div>
        </div>`;
    }

    function loadUsers({append = false} = {}) {
      if (_usersLoading) return Promise.resolve(null);
      _usersLoading = true;
      const list = document.getElementById('user-list');
      const moreBtn = document.getElementById('load-more-users-btn');
      const query = document.getElementById('user-search')?.value.trim() || '';
      const offset = append ? _usersOffset : 0;
      if (!append) {
        list.innerHTML = '<div class="empty-state">Loading users...</div>';
        _usersOffset = 0;
      }
      if (moreBtn) {
        moreBtn.disabled = true;
        moreBtn.textContent = 'Loading...';
      }
      return fetch(`/admin/api/users?offset=${offset}&limit=${USERS_PAGE_SIZE}&q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          if (!data.success) throw new Error(data.message || 'Failed to load users');
          const html = (data.users || []).map(userCardHtml).join('');
          if (append) {
            list.insertAdjacentHTML('beforeend', html);
          } else {
            list.innerHTML = html || '<div class="empty-state">No users found</div>';
          }
          _usersOffset = data.offset + data.users.length;
          _usersHasMore = data.has_more;
          if (moreBtn) {
            moreBtn.style.display = _usersHasMore ? 'inline-flex' : 'none';
            moreBtn.disabled = false;
            moreBtn.textContent = 'Load More';
          }
        })
        .catch(err => {
          if (!append) list.innerHTML = `<div class="empty-state">Failed to load users: ${escapeHtml(err.message)}</div>`;
          showToast('✗ ' + err.message, 'error');
        })
        .finally(() => {
          _usersLoading = false;
        });
    }

    function scheduleUserSearch() {
      clearTimeout(_usersSearchTimer);
      _usersSearchTimer = setTimeout(() => loadUsers(), 250);
    }

    function scrollLogsToBottom() {
      const logViewer = document.getElementById('log-viewer');
      if (logViewer) {
        logViewer.scrollTop = logViewer.scrollHeight;
      }
    }

    function ansiToHtml(text) {
      // ANSI 颜色代码映射
      const colors = {
        '30': '#000000', '31': '#cd3131', '32': '#0dbc79', '33': '#e5e510',
        '34': '#2472c8', '35': '#bc3fbc', '36': '#11a8cd', '37': '#e5e5e5',
        '90': '#666666', '91': '#f14c4c', '92': '#23d18b', '93': '#f5f543',
        '94': '#3b8eea', '95': '#d670d6', '96': '#29b8db', '97': '#ffffff',
        '40': '#000000', '41': '#cd3131', '42': '#0dbc79', '43': '#e5e510',
        '44': '#2472c8', '45': '#bc3fbc', '46': '#11a8cd', '47': '#e5e5e5'
      };

      let html = '';
      let currentStyle = '';

      // 转义 HTML 特殊字符
      text = text.replace(/&/g, '&amp;')
                 .replace(/</g, '&lt;')
                 .replace(/>/g, '&gt;');

      // 解析 ANSI 代码
      const parts = text.split(/\x1b\[([0-9;]+)m/);

      for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 0) {
          // 文本部分
          if (currentStyle) {
            html += '<span style="' + currentStyle + '">' + parts[i] + '</span>';
          } else {
            html += parts[i];
          }
        } else {
          // ANSI 代码部分
          const codes = parts[i].split(';');
          let styles = [];

          for (const code of codes) {
            if (code === '0' || code === '') {
              // 重置
              currentStyle = '';
            } else if (code === '1') {
              // 粗体
              styles.push('font-weight: bold');
            } else if (code === '4') {
              // 下划线
              styles.push('text-decoration: underline');
            } else if (colors[code]) {
              // 前景色
              if (code.startsWith('3') || code.startsWith('9')) {
                styles.push('color: ' + colors[code]);
              }
              // 背景色
              else if (code.startsWith('4')) {
                styles.push('background-color: ' + colors[code]);
              }
            }
          }

          currentStyle = styles.join('; ');
        }
      }

      return html;
    }

    let _rawLogs = '';
    let _logModules = [];
    let _activeLogModule = 'all';

    function parseLogModule(line) {
      const match = line.match(/\[([^\]\s][^\]]{0,40})\]/);
      return match ? match[1] : 'General';
    }

    function groupedLogLines() {
      const groups = new Map();
      for (const line of (_rawLogs || '').split('\n')) {
        const moduleName = parseLogModule(line);
        if (!groups.has(moduleName)) groups.set(moduleName, []);
        groups.get(moduleName).push(line);
      }
      return groups;
    }

    function setRawLogs(logText) {
      _rawLogs = logText || '';
      const groups = groupedLogLines();
      _logModules = [...groups.entries()]
        .map(([name, lines]) => ({name, count: lines.filter(Boolean).length}))
        .filter(item => item.count > 0)
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
      if (_activeLogModule !== 'all' && !_logModules.some(item => item.name === _activeLogModule)) {
        _activeLogModule = 'all';
      }
      renderLogs();
    }

    function selectLogModule(moduleName) {
      _activeLogModule = moduleName || 'all';
      renderLogs();
    }

    function renderLogModuleSummary(activeModule) {
      const summary = document.getElementById('log-module-summary');
      if (!summary) return;
      if (!_logModules.length) {
        summary.innerHTML = '';
        return;
      }
      summary.innerHTML = [
        `<button class="log-module-chip ${activeModule === 'all' ? 'active' : ''}" onclick="selectLogModule('all')">All ${_logModules.reduce((total, item) => total + item.count, 0)}</button>`,
        ..._logModules.map(item => `
          <button class="log-module-chip ${activeModule === item.name ? 'active' : ''}" data-log-module="${escapeHtml(item.name)}" onclick="selectLogModule(this.dataset.logModule)" title="${escapeHtml(item.name)}">
            ${escapeHtml(item.name)} ${item.count}
          </button>`)
      ].join('');
    }

    function renderLogs() {
      const logViewer = document.getElementById('log-viewer');
      if (!logViewer) return;
      const activeModule = _activeLogModule || 'all';
      const groups = groupedLogLines();
      const lines = activeModule === 'all'
        ? (_rawLogs || '').split('\n')
        : (groups.get(activeModule) || []);
      renderLogModuleSummary(activeModule);
      logViewer.innerHTML = ansiToHtml(lines.join('\n'));
      scrollLogsToBottom();
    }

    let _notificationsLoading = false;
    let _notificationsData = [];

    function notificationCopyText(item = {}) {
      const context = item.context || {};
      const contextText = Object.keys(context).length
        ? Object.entries(context).map(([key, value]) => `${key}: ${String(value)}`).join('\n')
        : '';
      return [
        `Title: ${item.title || 'Notification'}`,
        `Time: ${item.timestamp || item.time || 'Just now'}`,
        `User: ${item.user_id || 'Unknown'}`,
        contextText ? `Context:\n${contextText}` : '',
        `Details:\n${item.details || item.body || 'No details'}`
      ].filter(Boolean).join('\n\n');
    }

    function copyTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
      }
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.top = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(textarea);
      return ok ? Promise.resolve() : Promise.reject(new Error('Clipboard unavailable'));
    }

    function copyNotification(index) {
      const item = _notificationsData[index];
      if (!item) return;
      copyTextToClipboard(notificationCopyText(item))
        .then(() => showToast('✓ Notification copied'))
        .catch(err => showToast('✗ Copy failed: ' + err.message, 'error'));
    }

    function refreshNotifications({force = false} = {}) {
      if (_notificationsLoading && !force) return Promise.resolve(null);
      _notificationsLoading = true;
      return fetch('/admin/notifications')
        .then(res => res.json())
        .then(data => {
          const list = document.getElementById('notifications-list');
          const badge = document.getElementById('notification-badge');
          _notificationsData = Array.isArray(data) ? data : [];

          // 更新 badge
          if (_notificationsData.length > 0) {
            badge.textContent = _notificationsData.length;
            badge.style.display = 'inline';
          } else {
            badge.style.display = 'none';
          }

          if (_notificationsData.length === 0) {
            list.innerHTML = '<div style="text-align:center; opacity:0.5; padding:20px;">No notifications</div>';
            return;
          }

          list.className = 'notification-stack';
          list.innerHTML = _notificationsData.map((n, i) => {
            const context = n.context || {};
            const timestamp = n.timestamp || n.time || '';
            const details = n.details || n.body || '';
            const userId = n.user_id || 'Unknown';
            return `
              <div class="notification-card">
                <div class="notification-card-head" onclick="toggleNotification(${i})">
                  <div>
                    <div class="notification-title">${escapeHtml(n.title || 'Notification')}</div>
                    <div class="notification-meta">
                      ${timestamp ? escapeHtml(timestamp) : 'Just now'}
                      ${userId !== 'Unknown' ? ` · User ${escapeHtml(userId)}` : ''}
                    </div>
                  </div>
                  <div class="notification-head-actions">
                    <button class="btn notification-copy-btn" onclick="event.stopPropagation(); copyNotification(${i})">Copy</button>
                    <span id="notif-arrow-${i}" style="color:var(--text-tertiary);">+</span>
                  </div>
                </div>
                <div id="notif-detail-${i}" class="notification-detail">
                  ${Object.keys(context).length > 0 ? `
                    <div style="margin-bottom:10px; color:var(--text-tertiary); font-size:12px;">
                      ${Object.entries(context).map(([k,v]) => `<span style="margin-right:12px;"><b>${escapeHtml(k)}:</b> ${escapeHtml(String(v))}</span>`).join('')}
                    </div>` : ''}
                  <pre>${escapeHtml(details || 'No details')}</pre>
                </div>
              </div>
            `;
          }).join('');
        })
        .catch(() => {
          document.getElementById('notifications-list').innerHTML =
            '<div style="text-align:center; color:var(--danger-color); padding:20px;">Failed to load notifications</div>';
        })
        .finally(() => {
          _notificationsLoading = false;
        });
    }

    function toggleNotification(i) {
      const detail = document.getElementById(`notif-detail-${i}`);
      const arrow = document.getElementById(`notif-arrow-${i}`);
      const visible = detail.style.display !== 'none';
      detail.style.display = visible ? 'none' : 'block';
      arrow.textContent = visible ? '+' : '-';
    }

    function clearNotifications() {
      if (!confirm('Clear all notifications?')) return;
      fetch('/admin/notifications', { method: 'DELETE', headers: {'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken} })
        .then(res => res.json())
        .then(() => refreshNotifications());
    }

    function escapeHtml(str) {
      return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ===== DevToken Management =====
    function loadDevTokens() {
      const listEl = document.getElementById('devtoken-list');
      listEl.innerHTML = '<div style="text-align:center; padding:40px; opacity:0.5;">Loading tokens...</div>';

      fetch('/admin/devtokens')
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            listEl.innerHTML = `<div style="text-align:center; padding:40px; color:var(--danger-color);">Error: ${escapeHtml(data.message)}</div>`;
            return;
          }

          if (data.tokens.length === 0) {
            listEl.innerHTML = '<div style="text-align:center; padding:40px; opacity:0.5;">No developer tokens found</div>';
            return;
          }

          listEl.innerHTML = `
            <table style="width:100%; border-collapse:collapse; font-size:13px;">
              <thead>
                <tr style="border-bottom:2px solid var(--border-color); text-align:left;">
                  <th style="padding:10px 8px;">Token ID</th>
                  <th style="padding:10px 8px;">Note</th>
                  <th style="padding:10px 8px;">Created</th>
                  <th style="padding:10px 8px;">Last Used</th>
                  <th style="padding:10px 8px;">Users</th>
                  <th style="padding:10px 8px;">Status</th>
                  <th style="padding:10px 8px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${data.tokens.map(t => `
                  <tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:8px; font-family:monospace; font-size:12px;">${escapeHtml(t.token_id)}</td>
                    <td style="padding:8px;">${escapeHtml(t.note)}</td>
                    <td style="padding:8px; font-size:12px;">${escapeHtml(t.created_at)}</td>
                    <td style="padding:8px; font-size:12px;">${escapeHtml(t.last_used || 'Never')}</td>
                    <td style="padding:8px; font-size:12px;">${t.allowed_users_count}</td>
                    <td style="padding:8px;">
                      ${t.revoked
                        ? '<span style="color:var(--danger-color); font-weight:600;">Revoked</span>'
                        : '<span style="color:var(--success-color); font-weight:600;">Active</span>'}
                    </td>
                    <td style="padding:8px;">
                      ${!t.revoked
                        ? `<button class="btn btn-danger" style="font-size:11px; padding:4px 10px;" onclick="revokeDevToken('${escapeHtml(t.token_id)}')">Revoke</button>`
                        : `<button class="btn btn-danger" style="font-size:11px; padding:4px 10px;" onclick="deleteDevToken('${escapeHtml(t.token_id)}')">Delete</button>`}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>`;
        })
        .catch(err => {
          listEl.innerHTML = `<div style="text-align:center; padding:40px; color:var(--danger-color);">Network error: ${err}</div>`;
        });
    }

    function showCreateTokenModal() {
      document.getElementById('create-token-note').value = '';
      document.getElementById('createTokenModal').classList.add('show');
    }

    function closeCreateTokenModal() {
      document.getElementById('createTokenModal').classList.remove('show');
    }

    function closeTokenCreatedModal() {
      document.getElementById('tokenCreatedModal').classList.remove('show');
    }

    function createDevToken() {
      const note = document.getElementById('create-token-note').value.trim();
      if (!note) {
        alert('Please enter a note/description');
        return;
      }

      fetch('/admin/devtokens', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken},
        body: JSON.stringify({ note: note })
      })
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            alert('Failed to create token: ' + (data.message || 'Unknown error'));
            return;
          }
          closeCreateTokenModal();
          document.getElementById('created-token-id').textContent = data.token_id;
          document.getElementById('created-token-value').textContent = data.token;
          document.getElementById('tokenCreatedModal').classList.add('show');
          loadDevTokens();
        })
        .catch(err => alert('Network error: ' + err));
    }

    function copyCreatedToken() {
      const token = document.getElementById('created-token-value').textContent;
      navigator.clipboard.writeText(token).then(() => {
        alert('Token copied to clipboard');
      });
    }

    function revokeDevToken(tokenId) {
      if (!confirm('Revoke token ' + tokenId + '? This will disable API access.')) return;

      fetch('/admin/devtokens/' + tokenId, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken},
        body: JSON.stringify({ revoked: true })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            loadDevTokens();
          } else {
            alert('Failed to revoke: ' + (data.message || 'Unknown error'));
          }
        })
        .catch(err => alert('Network error: ' + err));
    }

    function deleteDevToken(tokenId) {
      if (!confirm('Permanently delete token ' + tokenId + '?')) return;

      fetch('/admin/devtokens/' + tokenId, {
        method: 'DELETE',
        headers: {'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken}
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            loadDevTokens();
          } else {
            alert('Failed to delete: ' + (data.message || 'Unknown error'));
          }
        })
        .catch(err => alert('Network error: ' + err));
    }

    // ===== Service Worker 注册（PWA 支持） =====
    let _swRegistration = null;
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js', { scope: '/admin/', updateViaCache: 'none' })
        .then(reg => {
          _swRegistration = reg;
          reg.update().catch(() => {});
        })
        .catch(() => {});

      // 收到 SW 消息（点击通知时跳转 tab 并刷新）
      navigator.serviceWorker.addEventListener('message', e => {
        if (e.data?.type === 'OPEN_TAB') {
          switchTab(e.data.tab || 'operations');
        }
      });
    }

    // ===== 浏览器通知开关（Web Push） =====
    function _urlB64ToUint8Array(b64) {
      const pad = '='.repeat((4 - b64.length % 4) % 4);
      const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
      return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
    }

    async function _getSubscription() {
      const reg = _swRegistration || await navigator.serviceWorker.ready;
      return reg.pushManager.getSubscription();
    }

    async function _applyNotifToggleUI() {
      const icon = document.getElementById('notif-toggle-icon');
      const label = document.getElementById('notif-toggle-label');
      const btn = document.getElementById('notif-toggle-btn');
      const sub = await _getSubscription().catch(() => null);
      if (sub) {
        icon.textContent = '✓';
        label.textContent = 'Notifications On';
        btn.style.borderColor = 'var(--accent-color)';
        btn.style.color = 'var(--accent-color)';
      } else {
        icon.textContent = '✕';
        label.textContent = 'Notifications Off';
        btn.style.borderColor = 'var(--border-color)';
        btn.style.color = 'var(--text-color)';
      }
    }

    async function toggleBrowserNotifications() {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        alert('Push notifications are not supported in this browser.');
        return;
      }

      try {
        const reg = await navigator.serviceWorker.ready;
        _swRegistration = reg;
        const sub = await reg.pushManager.getSubscription();

        if (sub) {
          // 关闭：取消订阅
          await sub.unsubscribe();
          fetch('/admin/push-subscription', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken },
            body: JSON.stringify({ endpoint: sub.endpoint })
          });
          _applyNotifToggleUI();
          return;
        }

        // 开启：请求权限 → 订阅 push
        if (Notification.permission === 'denied') {
          alert('Browser notifications are blocked. Please allow them in your browser settings.');
          return;
        }
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          alert('Notification permission was denied.');
          return;
        }

        const vapidRes = await fetch('/admin/vapid-public-key');
        if (!vapidRes.ok) {
          alert('Failed to fetch VAPID key: ' + vapidRes.status);
          return;
        }
        const vapidKey = await vapidRes.text();

        const newSub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: _urlB64ToUint8Array(vapidKey)
        });
        await fetch('/admin/push-subscription', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken },
          body: JSON.stringify(newSub.toJSON())
        });
        _applyNotifToggleUI();

      } catch (e) {
        alert('Notification error: ' + e.name + ': ' + e.message);
      }
    }

    // 初始化 UI 状态
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then(reg => {
        _swRegistration = reg;
        _applyNotifToggleUI();
      });
    }

    // 定期轮询：更新 badge，无 Push 订阅时作为 fallback 弹通知
    let _lastNotifCount = -1;  // -1 = 尚未初始化，首次不弹通知
    let _notificationPollLoading = false;

    async function pollNotificationBadge() {
      if (document.hidden || _notificationPollLoading) return;
      _notificationPollLoading = true;
      try {
        const res = await fetch('/admin/notifications');
        const data = await res.json();
        const badge = document.getElementById('notification-badge');
        if (data.length > 0) {
          badge.textContent = data.length;
          badge.style.display = 'inline';
        } else {
          badge.style.display = 'none';
        }

        if (_lastNotifCount === -1) {
          // 首次：仅初始化基线，不弹通知
          _lastNotifCount = data.length;
          return;
        }

        // 有新通知、有权限、且没有 Push 订阅时才用 fallback 弹
        if (data.length > _lastNotifCount && Notification.permission === 'granted') {
          const sub = await _getSubscription().catch(() => null);
          if (!sub) {
            const latest = data[0];
            new Notification(`JiETNG: ${latest.title}`, {
              body: `${latest.timestamp}${latest.user_id !== 'Unknown' ? '  User: ' + latest.user_id : ''}`,
              tag: 'jietng-fallback'
            });
          }
        }
        _lastNotifCount = data.length;
      } catch (_) {
      } finally {
        _notificationPollLoading = false;
      }
    }

    const _notificationPollTimer = setInterval(() => {
      pollNotificationBadge();
    }, 30000);

    window.addEventListener('pagehide', function() {
      clearInterval(_notificationPollTimer);
    });

    const _aiMonitorMessages = [];
    let _aiMonitorPendingImages = [];
    let _aiMonitorBusy = false;
    const _AI_MONITOR_JOB_KEY = 'jietng.admin.aiMonitorJob';
    const _AI_MONITOR_HEIGHT_KEY = 'jietng.admin.aiMonitorHeight';
    let _aiMonitorActiveJobId = '';
    let _aiMonitorPollTimer = null;
    let _aiMonitorPollFailures = 0;
    let _aiMonitorComposing = false;
    let _aiMonitorCompositionEndedAt = 0;
    let _aiMonitorStreamingMessage = null;
    let _aiMonitorStopRequested = false;
    let _aiMonitorJobAccepted = false;
    try {
      _aiMonitorActiveJobId = localStorage.getItem(_AI_MONITOR_JOB_KEY) || '';
    } catch (_) {
    }

    function aiMonitorHeightBounds() {
      const mobile = window.matchMedia('(max-width: 768px), (pointer: coarse)').matches;
      return {
        min: 96,
        max: Math.max(96, Math.min(mobile ? 620 : 760, window.innerHeight * (mobile ? 0.62 : 0.7)))
      };
    }

    function setAIMonitorHeight(value, persist = false) {
      const messages = document.getElementById('ai-monitor-messages');
      const handle = document.getElementById('ai-monitor-resize-handle');
      if (!messages || !handle) return;
      const bounds = aiMonitorHeightBounds();
      const height = Math.round(Math.min(bounds.max, Math.max(bounds.min, Number(value) || bounds.min)));
      messages.style.height = `${height}px`;
      handle.setAttribute('aria-valuemin', String(Math.round(bounds.min)));
      handle.setAttribute('aria-valuemax', String(Math.round(bounds.max)));
      handle.setAttribute('aria-valuenow', String(height));
      if (persist) {
        try {
          localStorage.setItem(_AI_MONITOR_HEIGHT_KEY, String(height));
        } catch (_) {
        }
      }
    }

    function initializeAIMonitorResize() {
      const messages = document.getElementById('ai-monitor-messages');
      const handle = document.getElementById('ai-monitor-resize-handle');
      if (!messages || !handle) return;
      let savedHeight = 0;
      try {
        savedHeight = Number(localStorage.getItem(_AI_MONITOR_HEIGHT_KEY)) || 0;
      } catch (_) {
      }
      if (savedHeight) setAIMonitorHeight(savedHeight);

      let drag = null;
      handle.addEventListener('pointerdown', function(event) {
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        event.preventDefault();
        drag = {
          pointerId: event.pointerId,
          startY: event.clientY,
          startHeight: messages.getBoundingClientRect().height
        };
        handle.classList.add('dragging');
        document.body.classList.add('ai-monitor-resizing');
        handle.setPointerCapture?.(event.pointerId);
      });
      handle.addEventListener('pointermove', function(event) {
        if (!drag || event.pointerId !== drag.pointerId) return;
        event.preventDefault();
        setAIMonitorHeight(drag.startHeight + event.clientY - drag.startY);
      });
      const finishDrag = function(event) {
        if (!drag || event.pointerId !== drag.pointerId) return;
        const height = messages.getBoundingClientRect().height;
        drag = null;
        handle.classList.remove('dragging');
        document.body.classList.remove('ai-monitor-resizing');
        setAIMonitorHeight(height, true);
      };
      handle.addEventListener('pointerup', finishDrag);
      handle.addEventListener('pointercancel', finishDrag);
      handle.addEventListener('lostpointercapture', finishDrag);
      handle.addEventListener('keydown', function(event) {
        const bounds = aiMonitorHeightBounds();
        let height = messages.getBoundingClientRect().height;
        if (event.key === 'ArrowUp') height -= event.shiftKey ? 72 : 24;
        else if (event.key === 'ArrowDown') height += event.shiftKey ? 72 : 24;
        else if (event.key === 'Home') height = bounds.min;
        else if (event.key === 'End') height = bounds.max;
        else return;
        event.preventDefault();
        setAIMonitorHeight(height, true);
      });
      if (!savedHeight) {
        handle.setAttribute('aria-valuenow', String(Math.round(messages.getBoundingClientRect().height)));
      }
    }

    initializeAIMonitorResize();

    async function optimizeAIMonitorImage(file) {
      if (file.size <= 850 * 1024 || !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
        return file;
      }
      const source = URL.createObjectURL(file);
      try {
        const image = new Image();
        image.src = source;
        await image.decode();
        const scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
        const context = canvas.getContext('2d');
        context.fillStyle = '#fff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);

        let blob = null;
        for (const quality of [0.82, 0.68, 0.55]) {
          blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
          if (blob && blob.size <= 850 * 1024) break;
        }
        if (!blob) return file;
        const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
        return new File([blob], name, {type: 'image/jpeg', lastModified: file.lastModified});
      } catch (_) {
        return file;
      } finally {
        URL.revokeObjectURL(source);
      }
    }

    async function copyAIMonitorText(value, button) {
      const original = button.textContent;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(value);
        } else {
          const fallback = document.createElement('textarea');
          fallback.value = value;
          fallback.style.position = 'fixed';
          fallback.style.opacity = '0';
          document.body.appendChild(fallback);
          fallback.select();
          document.execCommand('copy');
          fallback.remove();
        }
        button.textContent = 'Copied';
      } catch (_) {
        button.textContent = 'Copy failed';
      }
      setTimeout(() => { button.textContent = original; }, 1400);
    }

    function makeAIMonitorCopyButton(value, label, className = '') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `ai-monitor-copy ${className}`.trim();
      button.textContent = 'Copy';
      button.title = label;
      button.setAttribute('aria-label', label);
      button.addEventListener('click', () => copyAIMonitorText(value, button));
      return button;
    }

    function renderSafeAIHtml(container, renderedHtml, fallbackText) {
      if (!renderedHtml) {
        container.textContent = fallbackText;
        return;
      }
      const template = document.createElement('template');
      template.innerHTML = renderedHtml;
      const allowedTags = new Set([
        'A', 'BLOCKQUOTE', 'BR', 'CODE', 'DEL', 'EM', 'H1', 'H2', 'H3',
        'H4', 'H5', 'H6', 'HR', 'LI', 'OL', 'P', 'PRE', 'S', 'STRONG', 'TABLE',
        'TBODY', 'TD', 'TH', 'THEAD', 'TR', 'UL'
      ]);
      Array.from(template.content.querySelectorAll('*')).forEach((element) => {
        if (!allowedTags.has(element.tagName)) {
          if (['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'TEMPLATE'].includes(element.tagName)) {
            element.remove();
          } else {
            element.replaceWith(document.createTextNode(element.textContent || ''));
          }
          return;
        }
        Array.from(element.attributes).forEach((attribute) => {
          const keep = element.tagName === 'A' && ['href', 'title'].includes(attribute.name);
          if (!keep) element.removeAttribute(attribute.name);
        });
        if (element.tagName === 'A') {
          const href = element.getAttribute('href') || '';
          let allowed = href.startsWith('#');
          try {
            const target = new URL(href, window.location.origin);
            allowed = allowed || ['http:', 'https:', 'mailto:'].includes(target.protocol);
            if (allowed && target.origin !== window.location.origin && target.protocol !== 'mailto:') {
              element.target = '_blank';
              element.rel = 'noopener noreferrer';
            }
          } catch (_) {
            allowed = false;
          }
          if (!allowed) element.removeAttribute('href');
        }
      });
      template.content.querySelectorAll('table').forEach((table) => {
        const scroll = document.createElement('div');
        scroll.className = 'ai-monitor-table-scroll';
        table.replaceWith(scroll);
        scroll.appendChild(table);
      });
      container.replaceChildren(template.content);
      container.querySelectorAll('pre').forEach((pre) => {
        const code = pre.querySelector('code');
        const value = (code || pre).textContent || '';
        if (!value) return;
        pre.classList.add('ai-monitor-code-block');
        pre.appendChild(makeAIMonitorCopyButton(value, 'Copy code', 'ai-monitor-code-copy'));
      });
    }

    function renderAIMonitorReasoning(body, reasoning, renderedHtml) {
      let details = body.querySelector('.ai-monitor-reasoning');
      if (!reasoning) {
        details?.remove();
        return;
      }
      if (!details) {
        details = document.createElement('details');
        details.className = 'ai-monitor-reasoning';
        details.open = true;
        const summary = document.createElement('summary');
        summary.textContent = 'Reasoning summary';
        const text = document.createElement('div');
        text.className = 'ai-monitor-reasoning-text';
        details.append(summary, text);
        const answer = body.querySelector('.ai-monitor-message-text');
        answer ? body.insertBefore(details, answer) : body.appendChild(details);
      }
      renderSafeAIHtml(
        details.querySelector('.ai-monitor-reasoning-text'),
        renderedHtml,
        reasoning
      );
    }

    function renderAIMonitorReplyActions(body, content) {
      body.querySelector('.ai-monitor-message-actions')?.remove();
      if (!content) return;
      const actions = document.createElement('div');
      actions.className = 'ai-monitor-message-actions';
      actions.appendChild(makeAIMonitorCopyButton(content, 'Copy response'));
      body.appendChild(actions);
    }

    function renderAIMonitorMedia(body, images) {
      const signature = images.map((image) => image.src).join('\n');
      const existing = body.querySelector('.ai-monitor-message-media');
      if (existing?.dataset.signature === signature) return;
      existing?.remove();
      if (!images.length) return;
      const media = document.createElement('div');
      media.className = 'ai-monitor-message-media';
      media.dataset.signature = signature;
      images.forEach((image) => {
        const element = document.createElement('img');
        element.src = image.src;
        element.alt = image.alt || 'AI monitor image';
        element.loading = 'lazy';
        media.appendChild(element);
      });
      const actions = body.querySelector('.ai-monitor-message-actions');
      actions ? body.insertBefore(media, actions) : body.appendChild(media);
    }

    function appendAIMonitorMessage(
      role,
      content,
      images = [],
      renderedHtml = '',
      reasoning = '',
      reasoningHtml = '',
      remember = true
    ) {
      const container = document.getElementById('ai-monitor-messages');
      const empty = document.getElementById('ai-monitor-empty');
      if (!container) return;
      empty?.remove();

      const message = document.createElement('div');
      message.className = 'ai-monitor-message ' + role;
      const body = document.createElement('div');
      body.className = 'ai-monitor-message-body';
      const text = document.createElement('div');
      text.className = 'ai-monitor-message-text';
      if (role === 'assistant') {
        renderSafeAIHtml(text, renderedHtml, content);
      } else {
        text.textContent = content;
      }
      if (role === 'assistant') renderAIMonitorReasoning(body, reasoning, reasoningHtml);
      body.appendChild(text);

      renderAIMonitorMedia(body, images);
      if (role === 'assistant') renderAIMonitorReplyActions(body, content);
      message.appendChild(body);
      container.appendChild(message);
      container.scrollTop = container.scrollHeight;

      if (remember && (role === 'user' || role === 'assistant')) {
        const imageNote = images.length
          ? `\n[Images: ${images.map((image) => image.alt || 'image').join(', ')}]`
          : '';
        _aiMonitorMessages.push({role, content: content + imageNote});
        if (_aiMonitorMessages.length > 20) _aiMonitorMessages.shift();
      }
      return message;
    }

    function renderAIMonitorAttachments() {
      const container = document.getElementById('ai-monitor-attachments');
      if (!container) return;
      container.replaceChildren();
      container.hidden = _aiMonitorPendingImages.length === 0;
      _aiMonitorPendingImages.forEach((item, index) => {
        const preview = document.createElement('div');
        preview.className = 'ai-monitor-attachment';
        const image = document.createElement('img');
        image.src = item.url;
        image.alt = item.file.name;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '×';
        remove.setAttribute('aria-label', `Remove ${item.file.name}`);
        remove.addEventListener('click', () => removeAIMonitorImage(index));
        preview.append(image, remove);
        container.appendChild(preview);
      });
    }

    function selectAIMonitorImages(event) {
      const selected = Array.from(event.target.files || []);
      let rejected = false;
      for (const file of selected) {
        if (_aiMonitorPendingImages.length >= 3) {
          rejected = true;
          break;
        }
        if (file.size > 5 * 1024 * 1024) {
          rejected = true;
          continue;
        }
        _aiMonitorPendingImages.push({file, url: URL.createObjectURL(file)});
      }
      event.target.value = '';
      renderAIMonitorAttachments();
      if (rejected) {
        appendAIMonitorMessage('error', 'Use up to 3 PNG, JPEG, WebP, or HEIC images, 5MB each.');
      }
    }

    function removeAIMonitorImage(index) {
      const removed = _aiMonitorPendingImages.splice(index, 1)[0];
      if (removed) URL.revokeObjectURL(removed.url);
      renderAIMonitorAttachments();
    }

    function setAIMonitorBusy(busy) {
      _aiMonitorBusy = busy;
      const input = document.getElementById('ai-monitor-input');
      const button = document.getElementById('ai-monitor-send');
      const imageInput = document.getElementById('ai-monitor-images');
      const attach = document.getElementById('ai-monitor-attach');
      if (input) input.disabled = busy;
      if (imageInput) imageInput.disabled = busy;
      attach?.classList.toggle('disabled', busy);
      if (button) {
        button.disabled = false;
        button.classList.toggle('stop', busy);
        button.textContent = busy ? 'Stop' : 'Send';
      }
      setAIMonitorStatus(busy ? 'Checking' : 'Ready', busy);
    }

    function renderAIMonitorStatus(element, text, animated) {
      if (!element) return;
      const label = String(text || '').trim().replace(/[.\u2026]+$/, '') || 'Working';
      const animationState = animated ? 'true' : 'false';
      if (
        element.dataset.statusLabel === label
        && element.dataset.statusAnimated === animationState
      ) {
        return;
      }
      element.dataset.statusLabel = label;
      element.dataset.statusAnimated = animationState;
      element.replaceChildren(document.createTextNode(label));
      if (animated) {
        const dots = document.createElement('span');
        dots.className = 'ai-monitor-dots';
        dots.setAttribute('aria-hidden', 'true');
        for (let index = 0; index < 3; index += 1) {
          const dot = document.createElement('span');
          dot.textContent = '.';
          dots.appendChild(dot);
        }
        element.appendChild(dots);
      }
      element.setAttribute('aria-label', animated ? `${label}...` : label);
    }

    function setAIMonitorStatus(text, animated = _aiMonitorBusy) {
      const status = document.getElementById('ai-monitor-status');
      renderAIMonitorStatus(status, text, animated);
    }

    function rememberAIMonitorJob(jobId) {
      _aiMonitorActiveJobId = jobId;
      try {
        localStorage.setItem(_AI_MONITOR_JOB_KEY, jobId);
      } catch (_) {
      }
    }

    function clearAIMonitorJob() {
      if (_aiMonitorPollTimer) clearTimeout(_aiMonitorPollTimer);
      _aiMonitorPollTimer = null;
      _aiMonitorActiveJobId = '';
      _aiMonitorPollFailures = 0;
      _aiMonitorStopRequested = false;
      _aiMonitorJobAccepted = false;
      try {
        localStorage.removeItem(_AI_MONITOR_JOB_KEY);
      } catch (_) {
      }
    }

    function clearAIMonitorProgress() {
      _aiMonitorStreamingMessage?.remove();
      _aiMonitorStreamingMessage = null;
    }

    function updateAIMonitorProgress(data) {
      const answer = data.answer || '';
      const reasoning = data.reasoning || '';
      if (!_aiMonitorStreamingMessage) {
        _aiMonitorStreamingMessage = appendAIMonitorMessage(
          'assistant', '', [], '', '', '', false
        );
      }
      const body = _aiMonitorStreamingMessage.querySelector('.ai-monitor-message-body');
      let activity = body.querySelector('.ai-monitor-activity');
      if (!activity) {
        activity = document.createElement('div');
        activity.className = 'ai-monitor-activity';
        body.prepend(activity);
      }
      renderAIMonitorStatus(
        activity,
        data.activity || (answer ? 'Responding' : 'Thinking'),
        true
      );
      renderAIMonitorReasoning(body, reasoning, data.reasoning_html || '');
      renderSafeAIHtml(
        body.querySelector('.ai-monitor-message-text'),
        data.answer_html || '',
        answer
      );
      renderAIMonitorMedia(body, aiMonitorResponseImages(data.images));
      const container = document.getElementById('ai-monitor-messages');
      container.scrollTop = container.scrollHeight;
    }

    function aiMonitorResponseImages(images) {
      return (images || []).map((reference) => {
        const generated = reference.startsWith('generated:');
        const value = generated ? reference.slice('generated:'.length) : reference;
        return {
          src: generated
            ? `/admin/api/ai-monitor/image?token=${encodeURIComponent(value)}`
            : `/admin/api/ai-monitor/image?path=${encodeURIComponent(value)}`,
          alt: generated ? 'Generated image' : (value.split('/').pop() || 'AI monitor image')
        };
      });
    }

    function scheduleAIMonitorPoll(jobId, delay = 400) {
      if (_aiMonitorPollTimer) clearTimeout(_aiMonitorPollTimer);
      _aiMonitorPollTimer = setTimeout(() => pollAIMonitorJob(jobId), delay);
    }

    async function pollAIMonitorJob(jobId) {
      if (!jobId || jobId !== _aiMonitorActiveJobId) return;
      if (document.hidden) {
        setAIMonitorStatus('Waiting');
        return;
      }
      try {
        const response = await fetch(`/admin/api/ai-monitor/query/${encodeURIComponent(jobId)}`, {
          cache: 'no-store'
        });
        const data = await response.json().catch(() => ({}));
        _aiMonitorPollFailures = 0;
        if (response.status === 202) {
          _aiMonitorJobAccepted = true;
          updateAIMonitorProgress(data);
          setAIMonitorStatus(data.activity || 'Checking');
          scheduleAIMonitorPoll(jobId);
          return;
        }
        if (!response.ok || !data.success) {
          clearAIMonitorProgress();
          clearAIMonitorJob();
          setAIMonitorBusy(false);
          appendAIMonitorMessage('error', data.message || `HTTP ${response.status}`);
          return;
        }
        appendAIMonitorMessage(
          'assistant',
          data.answer || '',
          aiMonitorResponseImages(data.images),
          data.answer_html || '',
          data.reasoning || '',
          data.reasoning_html || ''
        );
        clearAIMonitorProgress();
        clearAIMonitorJob();
        setAIMonitorBusy(false);
        document.getElementById('ai-monitor-input')?.focus();
      } catch (_) {
        _aiMonitorPollFailures += 1;
        setAIMonitorStatus('Reconnecting');
        if (_aiMonitorPollFailures >= 8) {
          clearAIMonitorProgress();
          clearAIMonitorJob();
          setAIMonitorBusy(false);
          appendAIMonitorMessage('error', 'Could not reconnect to the diagnosis.');
        } else {
          scheduleAIMonitorPoll(jobId, 2000);
        }
      }
    }

    async function stopAIMonitor() {
      if (!_aiMonitorActiveJobId) return;
      _aiMonitorStopRequested = true;
      const button = document.getElementById('ai-monitor-send');
      if (button) button.disabled = true;
      setAIMonitorStatus('Stopping');
      if (!_aiMonitorJobAccepted) return;
      try {
        const response = await fetch(
          `/admin/api/ai-monitor/query/${encodeURIComponent(_aiMonitorActiveJobId)}`,
          {method: 'DELETE', headers: {'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken}}
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.success) throw new Error(data.message || `HTTP ${response.status}`);
        scheduleAIMonitorPoll(_aiMonitorActiveJobId, 100);
      } catch (error) {
        _aiMonitorStopRequested = false;
        if (button) button.disabled = false;
        setAIMonitorStatus('Stop failed', false);
        appendAIMonitorMessage('error', error.message || 'Could not stop the operation.');
      }
    }

    async function askAIMonitor(event) {
      event.preventDefault();
      if (_aiMonitorBusy) {
        stopAIMonitor();
        return;
      }

      const input = document.getElementById('ai-monitor-input');
      const question = input?.value.trim() || '';
      if (!question && !_aiMonitorPendingImages.length) return;

      const recentMessages = _aiMonitorMessages.slice(-20);
      const history = recentMessages.map(({role, content}) => ({role, content}));
      const currentImages = _aiMonitorPendingImages;
      appendAIMonitorMessage(
        'user',
        question,
        currentImages.map((item) => ({src: item.url, alt: item.file.name}))
      );
      _aiMonitorPendingImages = [];
      renderAIMonitorAttachments();
      input.value = '';
      clearAIMonitorProgress();
      _aiMonitorStopRequested = false;
      _aiMonitorJobAccepted = false;
      setAIMonitorBusy(true);

      const jobId = typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : Array.from(crypto.getRandomValues(new Uint8Array(18)), byte => byte.toString(16).padStart(2, '0')).join('');
      rememberAIMonitorJob(jobId);
      try {
        const payload = new FormData();
        payload.append('job_id', jobId);
        payload.append('question', question);
        payload.append('history', JSON.stringify(history));
        const uploadImages = await Promise.all(
          currentImages.map((item) => optimizeAIMonitorImage(item.file))
        );
        if (_aiMonitorStopRequested) {
          clearAIMonitorJob();
          setAIMonitorBusy(false);
          return;
        }
        uploadImages.forEach((file) => payload.append('images', file, file.name));
        const response = await fetch('/admin/api/ai-monitor/query', {
          method: 'POST',
          headers: {
            'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken
          },
          body: payload
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.success) {
          clearAIMonitorJob();
          setAIMonitorBusy(false);
          appendAIMonitorMessage('error', data.message || `HTTP ${response.status}`);
          return;
        }
        rememberAIMonitorJob(data.job_id || jobId);
        _aiMonitorJobAccepted = true;
        if (_aiMonitorStopRequested) {
          stopAIMonitor();
          return;
        }
        pollAIMonitorJob(_aiMonitorActiveJobId);
      } catch (_) {
        setAIMonitorStatus('Reconnecting');
        scheduleAIMonitorPoll(jobId, 1200);
      }
    }

    function handleAIMonitorKeydown(event) {
      const mobileInput = window.matchMedia('(max-width: 768px), (pointer: coarse)').matches;
      if (mobileInput) return;
      const selectingCandidate = _aiMonitorComposing
        || event.isComposing
        || event.keyCode === 229
        || Date.now() - _aiMonitorCompositionEndedAt < 150;
      if (event.key === 'Enter' && !event.shiftKey && !selectingCandidate) {
        event.preventDefault();
        document.getElementById('ai-monitor-form')?.requestSubmit();
      }
    }

    const _aiMonitorInput = document.getElementById('ai-monitor-input');
    _aiMonitorInput?.addEventListener('compositionstart', function() {
      _aiMonitorComposing = true;
    });
    _aiMonitorInput?.addEventListener('compositionend', function() {
      _aiMonitorComposing = false;
      _aiMonitorCompositionEndedAt = Date.now();
    });

    document.addEventListener('visibilitychange', function() {
      if (document.hidden) return;
      pollNotificationBadge();
      if (!_aiMonitorActiveJobId) return;
      setAIMonitorBusy(true);
      pollAIMonitorJob(_aiMonitorActiveJobId);
    });

    if (_aiMonitorActiveJobId) {
      _aiMonitorJobAccepted = true;
      setAIMonitorBusy(true);
      pollAIMonitorJob(_aiMonitorActiveJobId);
    }

    function refreshLogs() {
      fetch('/admin/get_logs')
        .then(res => res.json())
        .then(data => {
          setRawLogs(data.logs);
        })
        .catch(err => alert('Error refreshing logs: ' + err));
    }

    function refreshStats(btn) {
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Loading...';

      fetch('/admin/api/overview?refresh=' + Date.now(), {redirect: 'manual'})
        .then(res => {
          if (res.type === 'opaqueredirect' || res.status === 401 || res.status === 302) {
            throw new Error('Session expired, please re-login');
          }
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(data => {
          if (!data.success) throw new Error(data.message || 'Refresh failed');
          const s = data.stats;
          document.getElementById('overview-total-users').textContent = s.total_users;
          document.getElementById('overview-user-delta').textContent = `+${s.today_new_users} today`;
          document.getElementById('overview-user-segments').innerHTML = `
            <div class="monitor-segment"><strong>${s.jp_users}</strong>JP users</div>
            <div class="monitor-segment"><strong>${s.intl_users}</strong>INTL users</div>
            <div class="monitor-segment"><strong>${s.mau}</strong>MAU</div>
          `;
          document.getElementById('overview-dau').textContent = s.dau;
          document.getElementById('overview-wau').textContent = s.wau;
          document.getElementById('overview-stickiness').textContent = s.stickiness + '%';
          document.getElementById('overview-cpu').textContent = s.cpu_percent + '%';
          document.getElementById('overview-memory').textContent = `${s.memory_used_gb}/${s.total_memory} GB`;
          document.getElementById('overview-image-queue').textContent = `${s.image_queue_size}/${s.max_queue_size}`;
          document.getElementById('overview-web-queue').textContent = `${s.web_queue_size}/${s.max_queue_size}`;
          document.getElementById('overview-cpu-fill').style.width = Math.max(0, Math.min(100, s.cpu_percent)) + '%';
          document.getElementById('overview-memory-fill').style.width = Math.max(0, Math.min(100, s.memory_percent)) + '%';
          const imageQueuePct = s.max_queue_size ? (s.image_queue_size / s.max_queue_size * 100) : 0;
          const webQueuePct = s.max_queue_size ? (s.web_queue_size / s.max_queue_size * 100) : 0;
          document.getElementById('overview-image-queue-fill').style.width = Math.max(0, Math.min(100, imageQueuePct)) + '%';
          document.getElementById('overview-web-queue-fill').style.width = Math.max(0, Math.min(100, webQueuePct)) + '%';
          document.getElementById('stat-image-calls').textContent = s.today_image_calls;
          document.getElementById('stat-webhook-msgs').textContent = s.today_webhook_msgs;
          document.getElementById('stat-sync').textContent = `${s.today_sync_success} / ${s.today_sync_total}`;
          document.getElementById('stat-record-exports').textContent = s.today_record_exports;
          document.getElementById('stat-record-imports').textContent = s.today_record_imports;
          document.getElementById('stat-event-dropped').textContent = s.event_dropped;
          const successfulTasks = Math.max(0, s.total_tasks_processed - s.total_tasks_failed - s.total_tasks_timed_out);
          const successRate = s.total_tasks_processed ? (successfulTasks / s.total_tasks_processed * 100) : 100;
          document.getElementById('summary-uptime').textContent = s.uptime;
          document.getElementById('summary-task-success').textContent = successRate.toFixed(1) + '%';
          document.getElementById('summary-queue-backlog').textContent = s.image_queue_size + s.image_query_queue_size + s.web_queue_size;
          document.getElementById('summary-process-memory').textContent = s.process_memory_mb + ' MB';
          document.getElementById('summary-runtime').textContent = 'Python ' + s.python_version;
          document.getElementById('summary-host').textContent = s.hostname;
          showToast('✅ Stats refreshed', 'success');
          btn.disabled = false;
          btn.textContent = originalText;
        })
        .catch(err => {
          showToast('❌ ' + err.message, 'error');
          btn.disabled = false;
          btn.textContent = originalText;
        });
    }

    function updateDXData() {
      const btn = document.getElementById('update-dxdata-btn');
      btn.classList.add('btn-spinning');
      btn.disabled = true;
      fetch('/admin/update_dxdata', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
      })
      .then(res => res.json())
      .then(data => {
        btn.classList.remove('btn-spinning');
        btn.disabled = false;
        if (data.success) {
          const added = data.sheets_added || 0;
          showToast(added > 0 ? `✓ +${added} charts` : '✓ DXData up to date');
          loadDXDataStatus();
          startDXDataAudit();
        } else {
          showToast('✗ ' + (data.message || 'Failed to update DXData'), 'error');
        }
      })
      .catch(err => {
        btn.classList.remove('btn-spinning');
        btn.disabled = false;
        showToast('✗ Network error: ' + err, 'error');
      });
    }

    function clearNicknameCache() {
      if (confirm('Clear nickname cache? Saved nicknames will still be used until you manually refresh from LINE API.')) {
        fetch('/admin/clear_cache', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert('✅ Nickname cache cleared.');
          } else {
            alert('❌ Error: ' + (data.message || 'Unknown error'));
          }
        })
        .catch(err => alert('❌ Network error: ' + err));
      }
    }

    function loadAllNicknames(btn, refreshFromLine = false) {
      if (refreshFromLine && !confirm('Refresh all nicknames from LINE API? This may send one request per user.')) {
        return;
      }
      if (btn) {
        btn.classList.add('btn-spinning');
        btn.disabled = true;
      }
      const loadingIndicator = document.getElementById('nickname-loading');
      if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
      }
      fetch('/admin/load_nicknames', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({refresh: refreshFromLine})
      })
      .then(res => res.json())
      .then(data => {
        if (btn) {
          btn.classList.remove('btn-spinning');
          btn.disabled = false;
        }
        if (data.success) {
          if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
          }

          // 更新所有用户的昵称
          const nicknames = data.nicknames;
          for (const userId in nicknames) {
            const nicknameElement = document.querySelector('[data-user-id="' + userId + '"] .user-nickname');
            if (nicknameElement) {
              nicknameElement.textContent = nicknames[userId];
            }

            // 更新搜索用的 data 属性
            const userItem = document.querySelector('[data-user-id="' + userId + '"]');
            if (userItem) {
              userItem.setAttribute('data-nickname', nicknames[userId].toLowerCase());
            }
          }

          if (btn) showToast('✓ ' + (data.refreshed ? 'Refreshed ' : 'Loaded ') + data.count + ' nicknames');
        } else {
          console.error('Failed to load nicknames:', data.message);
          // 隐藏加载指示器即使失败
          if (loadingIndicator) {
            loadingIndicator.innerHTML = '<span style="color: var(--danger-color);">⚠️ Failed to load nicknames</span>';
          }
          if (btn) showToast('✗ Failed to load nicknames', 'error');
        }
      })
      .catch(err => {
        if (btn) {
          btn.classList.remove('btn-spinning');
          btn.disabled = false;
        }
        console.error('Error loading nicknames:', err);
        if (loadingIndicator) {
          loadingIndicator.innerHTML = '<span style="color: var(--danger-color);">⚠️ Network error</span>';
        }
        if (btn) showToast('✗ Network error', 'error');
      });
    }

    // ==================== Notice Management Functions ====================

    function loadNotices() {
      fetch('/admin/get_notices')
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            displayNotices(data.notices);
          } else {
            showToast('✗ Failed to load notices: ' + data.message);
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    function displayNotices(notices) {
      const container = document.getElementById('notices-list');

      if (!notices || notices.length === 0) {
        container.innerHTML = '<div class="empty-state">No notices found</div>';
        return;
      }

      const html = notices.map(notice => {
        const content = typeof notice.content === 'string'
          ? {[defaultLanguage]: notice.content}
          : (notice.content || {});

        const statusBadge = notice.status === 'draft'
          ? '<span class="badge" style="color:var(--warning-color);border-color:var(--warning-color);">Draft</span>'
          : '<span class="badge" style="color:var(--success-color);border-color:var(--success-color);">Published</span>';
        const votingBadge = notice.voting_enabled
          ? '<span class="badge" style="color:var(--info-color);border-color:var(--info-color);">Voting</span>'
          : '';

        const actionBtns = [
          notice.status === 'published' ? `<button class="btn btn-primary" onclick="showNoticeStats('${notice.id}')">Stats</button>` : '',
          notice.status === 'draft'     ? `<button class="btn btn-success" onclick="publishDraft('${notice.id}')">Publish</button>` : '',
          `<button class="btn btn-warning" onclick="editNotice('${notice.id}')">Edit</button>`,
          `<button class="btn btn-danger"  onclick="deleteNoticeConfirm('${notice.id}')">Delete</button>`,
        ].filter(Boolean).join('');

        const buttonRow = notice.button ? `
          <div class="notice-button-meta">
            <span>Button</span>
            <span style="font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(notice.button.value || '')}">${escapeHtml(notice.button.type || '')} · ${escapeHtml(notice.button.value || '')}</span>
          </div>` : '';

        const contentRows = languageOptions.map(({code, label}) => `
          <div class="notice-content-row">
            <div class="notice-lang">${escapeHtml(label)}</div>
            <div class="notice-text">${escapeHtml(content[code] || '—')}</div>
          </div>`).join('');

        return `
          <article class="notice-card">
            <div class="notice-card-head">
              <div>
                <div class="notice-card-title">Notice</div>
                <div class="notice-card-meta">${escapeHtml(notice.id)} · ${escapeHtml(notice.date || '')}</div>
              </div>
              <div class="notice-badges">
                ${statusBadge}${votingBadge}
              </div>
            </div>
            <div class="notice-content-grid">${contentRows}</div>
            ${buttonRow}
            <div class="notice-actions">${actionBtns}</div>
          </article>`;
      }).join('');
      container.innerHTML = html;
    }

    function toggleNoticeButtonFields() {
      const hasButton = document.getElementById('notice-has-button').checked;
      document.getElementById('noticeButtonFields').style.display = hasButton ? 'block' : 'none';
    }

    function showCreateNoticeModal() {
      document.getElementById('notice-modal-title').textContent = 'Create New Notice';
      document.getElementById('notice-id').value = '';
      setLocalizedValues('.notice-content-input');
      document.getElementById('notice-voting-enabled').checked = false;
      document.getElementById('notice-status').value = 'published';
      document.getElementById('notice-has-button').checked = false;
      document.getElementById('noticeButtonFields').style.display = 'none';
      document.getElementById('notice-button-type').value = 'uri';
      setLocalizedValues('.notice-button-label-input');
      document.getElementById('notice-button-value').value = '';
      document.getElementById('notice-save-btn').textContent = 'Create';
      document.getElementById('noticeModal').classList.add('show');
    }

    function editNotice(noticeId) {
      fetch('/admin/get_notices')
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            const notice = data.notices.find(n => n.id === noticeId);
            if (notice) {
              document.getElementById('notice-modal-title').textContent = 'Edit Notice';
              document.getElementById('notice-id').value = notice.id;

              // Handle multi-language content
              const content = notice.content;
              if (typeof content === 'string') {
                setLocalizedValues('.notice-content-input', {[defaultLanguage]: content});
              } else {
                setLocalizedValues('.notice-content-input', content);
              }

              document.getElementById('notice-voting-enabled').checked = notice.voting_enabled || false;
              document.getElementById('notice-status').value = notice.status || 'published';

              // Load button data
              if (notice.button) {
                document.getElementById('notice-has-button').checked = true;
                document.getElementById('noticeButtonFields').style.display = 'block';
                document.getElementById('notice-button-type').value = notice.button.type || 'uri';
                setLocalizedValues('.notice-button-label-input', notice.button.label);
                document.getElementById('notice-button-value').value = notice.button.value || '';
              } else {
                document.getElementById('notice-has-button').checked = false;
                document.getElementById('noticeButtonFields').style.display = 'none';
                setLocalizedValues('.notice-button-label-input');
                document.getElementById('notice-button-value').value = '';
              }

              document.getElementById('notice-save-btn').textContent = 'Update';
              document.getElementById('noticeModal').classList.add('show');
            }
          }
        });
    }

    function saveNotice(event) {
      event.preventDefault();

      const noticeId = document.getElementById('notice-id').value;
      const content = localizedValues('.notice-content-input');
      const votingEnabled = document.getElementById('notice-voting-enabled').checked;
      const status = document.getElementById('notice-status').value;

      // Validate at least one language
      if (!Object.values(content).some(Boolean)) {
        showToast('✗ At least one language content is required');
        return;
      }

      const isUpdate = !!noticeId;
      const url = isUpdate ? '/admin/update_notice' : '/admin/create_notice';
      const payload = {
        content,
        voting_enabled: votingEnabled,
        status: status
      };

      if (isUpdate) {
        payload.notice_id = noticeId;
      }

      // Add button data
      const hasButton = document.getElementById('notice-has-button').checked;
      if (hasButton) {
        payload.button_type = document.getElementById('notice-button-type').value;
        payload.button_label = localizedValues('.notice-button-label-input');
        payload.button_value = document.getElementById('notice-button-value').value;
      } else if (isUpdate) {
        payload.remove_button = true;
      }

      const btn = document.getElementById('notice-save-btn');
      btn.disabled = true;
      btn.textContent = isUpdate ? 'Updating...' : 'Creating...';

      fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast(`✓ Notice ${isUpdate ? 'updated' : 'created'} successfully`);
          closeNoticeModal();
          loadNotices();
        } else {
          showToast('✗ ' + data.message);
        }
        btn.disabled = false;
        btn.textContent = isUpdate ? 'Update' : 'Create';
      })
      .catch(err => {
        showToast('✗ Network error: ' + err);
        btn.disabled = false;
        btn.textContent = isUpdate ? 'Update' : 'Create';
      });
    }

    function deleteNoticeConfirm(noticeId) {
      if (!confirm('Are you sure you want to delete this notice?\n\nThis action cannot be undone.')) {
        return;
      }

      fetch('/admin/delete_notice', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({notice_id: noticeId})
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast('✓ Notice deleted successfully');
          loadNotices();
        } else {
          showToast('✗ ' + data.message);
        }
      })
      .catch(err => {
        showToast('✗ Network error: ' + err);
      });
    }

    function closeNoticeModal() {
      document.getElementById('noticeModal').classList.remove('show');
      document.getElementById('noticeForm').reset();
    }

    function showNoticeStats(noticeId) {
      fetch(`/admin/get_notice_stats?notice_id=${noticeId}`)
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            displayNoticeStats(data.stats);
            document.getElementById('noticeStatsModal').classList.add('show');
          } else {
            showToast('✗ Failed to load statistics');
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    function displayNoticeStats(stats) {
      const container = document.getElementById('stats-content');

      const supportPct = stats.support_count + stats.oppose_count > 0
        ? (stats.support_count / (stats.support_count + stats.oppose_count) * 100).toFixed(1)
        : 0;
      const opposePct = stats.support_count + stats.oppose_count > 0
        ? (stats.oppose_count / (stats.support_count + stats.oppose_count) * 100).toFixed(1)
        : 0;

      container.innerHTML = `
        <div style="margin-bottom: 24px;">
          <h3 style="font-size: 14px; color: #666; margin-bottom: 12px;">📖 Read Statistics</h3>
          <div style="padding: 16px; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Total Users:</span>
              <strong>${stats.total_users}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Read Count:</span>
              <strong style="color: #17B169;">${stats.read_count}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span>Read Percentage:</span>
              <strong style="color: #17B169;">${stats.read_percentage}%</strong>
            </div>

            <!-- Progress bar -->
            <div style="margin-top: 12px; background: #E9ECEF; height: 8px; border-radius: 4px; overflow: hidden;">
              <div style="width: ${stats.read_percentage}%; height: 100%; background: linear-gradient(90deg, #17B169, #28C76F); transition: width 0.3s;"></div>
            </div>
          </div>
        </div>

        <div>
          <h3 style="font-size: 14px; color: #666; margin-bottom: 12px;">🗳️ Voting Statistics</h3>
          <div style="padding: 16px; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Support:</span>
              <strong style="color: #17B169;">${stats.support_count} (${supportPct}%)</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>Oppose:</span>
              <strong style="color: #FF3B30;">${stats.oppose_count} (${opposePct}%)</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <span>No Vote:</span>
              <strong style="color: #999;">${stats.no_vote_count}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span>Vote Participation:</span>
              <strong>${stats.vote_percentage}%</strong>
            </div>

            <!-- Vote visualization -->
            <div style="margin-top: 12px; display: flex; height: 8px; border-radius: 4px; overflow: hidden;">
              <div style="width: ${supportPct}%; background: #17B169;"></div>
              <div style="width: ${opposePct}%; background: #FF3B30;"></div>
            </div>
          </div>
        </div>
      `;
    }

    function closeStatsModal() {
      document.getElementById('noticeStatsModal').classList.remove('show');
    }

    function publishDraft(noticeId) {
      if (!confirm('Are you sure you want to publish this draft?\n\nThis will send the notice to all users.')) {
        return;
      }

      fetch('/admin/publish_notice', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({notice_id: noticeId})
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Notice published successfully');
            loadNotices();
          } else {
            showToast('✗ ' + data.message);
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
      const noticeModal = document.getElementById('noticeModal');
      if (event.target === noticeModal) {
        closeNoticeModal();
      }
    });

    // Load notices when notices tab is opened
    document.addEventListener('DOMContentLoaded', function() {
      if (document.getElementById('notices-tab').classList.contains('active')) {
        loadNotices();
      }
    });

    // ==================== DxData Functions ====================

    function loadDXDataStatus() {
      const container = document.getElementById('dxdata-status-container');
      container.innerHTML = '<div style="text-align: center; padding: 40px; opacity: 0.5;">Loading...</div>';

      fetch('/admin/dxdata_status')
        .then(res => res.json())
        .then(data => {
          displayDXDataStatus(data);
        })
        .catch(err => {
          container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger-color);">Network error: ' + err + '</div>';
        });
    }

    function toggleVersionList() {
      const list = document.getElementById('version-list');
      const chevron = document.getElementById('version-chevron');
      if (!list) return;
      const open = list.style.display === 'none';
      list.style.display = open ? 'block' : 'none';
      chevron.style.transform = open ? 'rotate(90deg)' : '';
    }

    function displayDXDataStatus(data) {
      const container = document.getElementById('dxdata-status-container');

      const html = `
        <div class="list-panel" style="margin-bottom: 12px;">
          <div class="list-item" onclick="toggleVersionList()" style="cursor: pointer; user-select: none;">
            <span style="color: var(--text-secondary);">Versions</span>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-weight: 600; font-family: monospace;">${data.versions}</span>
              <span id="version-chevron" style="font-size: 11px; color: var(--text-tertiary); transition: transform 0.2s;">▶</span>
            </div>
          </div>
          <div id="version-list" style="display: none;">
            ${(data.version_names || []).map((v, i) => `
              <div class="list-item" style="padding-left: 20px;">
                <span style="color: var(--text-tertiary); font-size: 12px; font-family: monospace;">${String(i + 1).padStart(2, '0')}</span>
                <span style="font-size: 13px; color: var(--text-secondary);">${escapeHtml(v)}</span>
              </div>`).join('')}
          </div>
        </div>
        <div class="list-panel" style="margin-bottom: 12px;">
          <div class="list-panel-header">Songs</div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">Total</span>
            <span style="font-weight: 600; font-family: monospace;">${data.songs.total}</span>
          </div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">Standard</span>
            <span style="font-weight: 600; font-family: monospace;">${data.songs.std}</span>
          </div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">DX</span>
            <span style="font-weight: 600; font-family: monospace;">${data.songs.dx}</span>
          </div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">UTAGE</span>
            <span style="font-weight: 600; font-family: monospace;">${data.songs.utage}</span>
          </div>
        </div>
        <div class="list-panel">
          <div class="list-panel-header">Charts</div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">Total</span>
            <span style="font-weight: 600; font-family: monospace;">${data.sheets.total}</span>
          </div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">JP</span>
            <span style="font-weight: 600; font-family: monospace;">${data.sheets.jp}</span>
          </div>
          <div class="list-item">
            <span style="color: var(--text-secondary);">INTL</span>
            <span style="font-weight: 600; font-family: monospace;">${data.sheets.intl}</span>
          </div>
        </div>
      `;

      container.innerHTML = html;
    }

    // ========== Backup Management ==========
    function createBackup() {
      const btn = document.getElementById('create-backup-btn');
      btn.disabled = true;
      btn.textContent = 'Creating...';

      fetch('/admin/backups', {
        method: 'POST',
        headers: {'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken}
      })
        .then(res => res.json())
        .then(data => {
          btn.disabled = false;
          btn.textContent = 'Create';
          if (data.success) {
            alert(data.message || 'Backup created successfully');
            loadBackups();
          } else {
            alert('Failed: ' + (data.message || 'Unknown error'));
          }
        })
        .catch(err => {
          btn.disabled = false;
          btn.textContent = 'Create';
          alert('Network error: ' + err);
        });
    }

    function loadBackups() {
      const listEl = document.getElementById('backups-list');
      listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-tertiary);">Loading backups...</div>';

      fetch('/admin/get_backups')
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            listEl.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--danger-color);">Error: ${data.message}</div>`;
            return;
          }

          if (data.backups.length === 0) {
            listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-tertiary);">No backup files found</div>';
            return;
          }

          displayBackups(data.backups);
        })
        .catch(err => {
          listEl.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--danger-color);">Network error: ${err}</div>`;
        });
    }

    function displayBackups(backups) {
      const listEl = document.getElementById('backups-list');

      if (backups.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No backup files found.</div>';
        return;
      }

      let html = `
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
          <thead>
            <tr style="border-bottom:2px solid var(--border-color); text-align:left;">
              <th style="padding:10px 8px;">Filename</th>
              <th style="padding:10px 8px;">Size</th>
              <th style="padding:10px 8px;">Created At</th>
              <th style="padding:10px 8px;">Actions</th>
            </tr>
          </thead>
          <tbody>
      `;

      backups.forEach(backup => {
        html += `
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:8px; font-family:monospace; font-size:12px;">${backup.filename}</td>
            <td style="padding:8px; font-size:12px;">${backup.size_mb} MB</td>
            <td style="padding:8px; font-size:12px;">${backup.created_at}</td>
            <td style="padding:8px;">
              <button onclick="downloadBackup('${backup.filename}')" class="btn btn-primary" style="font-size:11px; padding:4px 10px;">Download</button>
              <button onclick="deleteBackup('${backup.filename}')" class="btn btn-danger" style="font-size:11px; padding:4px 10px;">Delete</button>
            </td>
          </tr>
        `;
      });

      html += '</tbody></table>';
      listEl.innerHTML = html;
    }

    function downloadBackup(filename) {
      window.location.href = `/admin/download_backup?file=${encodeURIComponent(filename)}`;
      showToast('Downloading ' + filename);
    }

    function deleteBackup(filename) {
      if (!confirm(`Are you sure you want to delete this backup?\n\n${filename}\n\nThis action cannot be undone.`)) {
        return;
      }

      fetch('/admin/delete_backup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filename: filename})
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Backup deleted successfully');
            loadBackups(); // Reload the list
          } else {
            showToast('✗ ' + data.message);
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    // ==================== Tip/Ad Management Functions ====================

    function loadTipAds() {
      fetch('/admin/tip_ads')
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            displayTipAds(data.tip_ads);
          } else {
            showToast('✗ Failed to load tip/ads');
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    function displayTipAds(tipads) {
      const container = document.getElementById('tipadList');
      if (tipads.length === 0) {
        container.innerHTML = '<div class="empty-state">No tip/ads found. Create one to get started!</div>';
        return;
      }

      const html = '<div class="tipad-list">' + tipads.map(tipad => {
        const typeLabel = tipad.type === 'ad' ? 'AD' : 'TIP';
        const enabledBadge = tipad.enabled
          ? '<span class="badge badge-success">ON</span>'
          : '<span class="badge badge-secondary">OFF</span>';

        const buttonRow = tipad.button ? `
          <div class="tipad-button-meta">
            <span>Button</span>
            <span style="font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(tipad.button.value)}">${escapeHtml(tipad.button.type)} · ${escapeHtml(tipad.button.value)}</span>
          </div>` : '';

        return `
          <article class="tipad-card">
            <div class="tipad-card-head">
              <div>
                <div class="tipad-title">${typeLabel}</div>
                <div class="tipad-meta">${escapeHtml(tipad.id)} · ${escapeHtml(tipad.created_at || '')}</div>
              </div>
              <div class="tipad-status">
                ${enabledBadge}
              </div>
            </div>
            <div class="notice-content-grid">
              ${languageOptions.map(({code, label}) => `
                <div class="notice-content-row">
                  <div class="notice-lang">${escapeHtml(label)}</div>
                  <div class="notice-text">${escapeHtml((tipad.text || {})[code] || '—')}</div>
                </div>`).join('')}
            </div>
            ${buttonRow}
            <div class="tipad-actions">
              <button class="btn btn-warning" onclick="editTipAd('${tipad.id}')">Edit</button>
              <button class="btn btn-danger" onclick="deleteTipAd('${tipad.id}')">Delete</button>
            </div>
          </article>`;
      }).join('') + '</div>';
      container.innerHTML = html;
    }

    function showCreateTipAdForm() {
      document.getElementById('tipadFormTitle').textContent = 'Create Tip/Ad';
      document.getElementById('tipadForm').reset();
      document.getElementById('tipad_id').value = '';
      document.getElementById('tipad_enabled').checked = true;
      document.getElementById('tipad_has_button').checked = false;
      document.getElementById('buttonFields').style.display = 'none';
      document.getElementById('tipadFormModal').classList.add('show');
    }

    function editTipAd(tipAdId) {
      fetch(`/admin/tip_ads/${tipAdId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            const tipad = data.tip_ad;
            if (tipad) {
              document.getElementById('tipadFormTitle').textContent = 'Edit Tip/Ad';
              document.getElementById('tipad_id').value = tipad.id;
              document.getElementById('tipad_type').value = tipad.type;
              setLocalizedValues('.tipad-text-input', tipad.text);
              document.getElementById('tipad_enabled').checked = tipad.enabled;

              if (tipad.button) {
                document.getElementById('tipad_has_button').checked = true;
                document.getElementById('buttonFields').style.display = 'block';
                document.getElementById('tipad_button_type').value = tipad.button.type;
                setLocalizedValues('.tipad-button-label-input', tipad.button.label);
                document.getElementById('tipad_button_value').value = tipad.button.value || '';
              } else {
                document.getElementById('tipad_has_button').checked = false;
                document.getElementById('buttonFields').style.display = 'none';
                setLocalizedValues('.tipad-button-label-input');
                document.getElementById('tipad_button_value').value = '';
              }

              document.getElementById('tipadFormModal').classList.add('show');
            }
          }
        })
        .catch(err => {
          showToast('✗ Failed to load tip/ad: ' + err);
        });
    }

    function closeTipAdForm() {
      document.getElementById('tipadFormModal').classList.remove('show');
    }

    function toggleButtonFields() {
      const hasButton = document.getElementById('tipad_has_button').checked;
      document.getElementById('buttonFields').style.display = hasButton ? 'block' : 'none';
    }

    function saveTipAd(event) {
      event.preventDefault();

      const tipAdId = document.getElementById('tipad_id').value;
      const hasButton = document.getElementById('tipad_has_button').checked;

      const data = {
        type: document.getElementById('tipad_type').value,
        text: localizedValues('.tipad-text-input'),
        enabled: document.getElementById('tipad_enabled').checked
      };

      if (!Object.values(data.text).some(Boolean)) {
        showToast('✗ At least one language text is required');
        return;
      }

      if (tipAdId) {
        data.id = tipAdId;
      }

      if (hasButton) {
        data.button_type = document.getElementById('tipad_button_type').value;
        data.button_label = localizedValues('.tipad-button-label-input');
        data.button_value = document.getElementById('tipad_button_value').value;
      } else if (tipAdId) {
        data.remove_button = true;
      }

      const url = tipAdId ? `/admin/tip_ads/${tipAdId}` : '/admin/tip_ads';
      const load_method = tipAdId ? 'PUT' : 'POST';

      fetch(url, {
        method: load_method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Tip/Ad saved successfully');
            closeTipAdForm();
            loadTipAds();
          } else {
            showToast('✗ ' + data.message);
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    function deleteTipAd(tipAdId) {
      if (!confirm('Are you sure you want to delete this tip/ad?')) {
        return;
      }

      fetch(`/admin/tip_ads/${tipAdId}`, {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: tipAdId})
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Tip/Ad deleted successfully');
            loadTipAds();
          } else {
            showToast('✗ ' + data.message);
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    // ==================== Background Management Functions ====================

    function loadBackgrounds() {
      const grid = document.getElementById('admin-bg-grid');
      grid.innerHTML = '<div style="text-align:center; padding:30px 40px; color:var(--text-tertiary); white-space:nowrap;">Loading...</div>';

      fetch('/admin/backgrounds')
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            grid.innerHTML = `<div style="text-align:center; padding:30px 40px; color:var(--danger-color); white-space:nowrap;">Error: ${data.message}</div>`;
            return;
          }
          displayBackgrounds(data.files);
        })
        .catch(err => {
          grid.innerHTML = `<div style="text-align:center; padding:30px 40px; color:var(--danger-color); white-space:nowrap;">Network error: ${err}</div>`;
        });
    }

    function displayBackgrounds(files) {
      const grid = document.getElementById('admin-bg-grid');
      const countEl = document.getElementById('admin-bg-count');
      countEl.textContent = files.length + ' images';

      if (!files.length) {
        grid.innerHTML = '<div style="text-align:center; padding:30px 40px; color:var(--text-tertiary); white-space:nowrap;">No background images found</div>';
        return;
      }

      grid.innerHTML = files.map(f => `
        <div class="admin-bg-option">
          <img src="/static/pics/bg/${f.name}?t=${Date.now()}" alt="${f.name}" loading="lazy" />
          <div class="bg-size">${f.size}</div>
          <div class="bg-label" title="${f.name}">${f.name}</div>
          <button class="bg-delete-btn" onclick="event.stopPropagation(); deleteBackground('${f.name}')">×</button>
          ${f.is_user ? '<span class="bg-user-badge">User</span>' : ''}
        </div>
      `).join('');
    }

    function onAdminFileSelected(input) {
      const area = document.getElementById('admin-upload-area');
      const icon = document.getElementById('admin-upload-icon');
      const text = document.getElementById('admin-upload-text');
      const btn = document.getElementById('admin-upload-btn');
      if (input.files && input.files.length > 0) {
        area.classList.add('has-file');
        icon.textContent = '✓';
        text.textContent = input.files[0].name;
        btn.style.display = 'block';
      } else {
        area.classList.remove('has-file');
        icon.textContent = '+';
        text.textContent = 'Choose Image';
        btn.style.display = 'none';
      }
    }

    function uploadBackground() {
      const input = document.getElementById('bg-upload-input');
      if (!input.files.length) return;

      const file = input.files[0];
      const ext = file.name.split('.').pop().toLowerCase();
      if (!['png', 'jpg', 'jpeg', 'webp', 'heic', 'heif'].includes(ext)) {
        showToast('✗ Only PNG, JPG, WebP, HEIC are supported');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        showToast('✗ File too large (max 10MB)');
        return;
      }

      const btn = document.getElementById('admin-upload-btn');
      btn.disabled = true;

      const formData = new FormData();
      formData.append('file', file);

      fetch('/admin/backgrounds', {
        method: 'POST',
        body: formData
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Uploaded: ' + data.filename);
            input.value = '';
            // 重置上传区域
            const area = document.getElementById('admin-upload-area');
            area.classList.remove('has-file');
            document.getElementById('admin-upload-icon').textContent = '+';
            document.getElementById('admin-upload-text').textContent = 'Choose Image';
            btn.style.display = 'none';
            btn.disabled = false;
            loadBackgrounds();
          } else {
            showToast('✗ ' + (data.message || 'Upload failed'));
            btn.disabled = false;
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
          btn.disabled = false;
        });
    }

    function deleteBackground(filename) {
      if (!confirm(`Delete "${filename}"?`)) return;

      fetch('/admin/backgrounds/' + encodeURIComponent(filename), {
        method: 'DELETE'
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showToast('✓ Deleted: ' + filename);
            loadBackgrounds();
          } else {
            showToast('✗ ' + (data.message || 'Delete failed'));
          }
        })
        .catch(err => {
          showToast('✗ Network error: ' + err);
        });
    }

    var _cmdLabels = {
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

    function _loadDateData(date) {
      if (!date) return;
      var today = new Date().getFullYear() + '-' + String(new Date().getMonth()+1).padStart(2,'0') + '-' + String(new Date().getDate()).padStart(2,'0');
      var isToday = (date === today);
      var titleEl = document.getElementById('activity-title');
      if (titleEl) titleEl.textContent = isToday ? "Today's Activity" : date + ' Activity';

      fetch('/admin/api/hourly?date=' + date)
        .then(function(r) { return r.json(); })
        .then(function(data) {
          // Hourly chart
          var chart = document.getElementById('hourly-chart');
          var hourly = data.hourly || [];
          var maxV = Math.max.apply(null, hourly) || 1;
          var html = '';
          for (var i = 0; i < 24; i++) {
            var v = hourly[i] || 0;
            var opacity = (0.25 + 0.75 * v / maxV).toFixed(2);
            var height = (10 + 90 * v / maxV).toFixed(1);
            html += '<div title="' + i + ':00 — ' + v + '" style="background:var(--accent-color);opacity:' + opacity + ';height:' + height + '%;border-radius:3px 3px 0 0;"></div>';
          }
          if (chart) chart.innerHTML = html;

          // Activity cards
          var el;
          if ((el = document.getElementById('stat-image-calls'))) el.textContent = data.image_calls || 0;
          if ((el = document.getElementById('stat-webhook-msgs'))) el.textContent = data.webhook_msgs || 0;
          if ((el = document.getElementById('stat-record-exports'))) el.textContent = data.record_exports || 0;
          if ((el = document.getElementById('stat-record-imports'))) el.textContent = data.record_imports || 0;
          if ((el = document.getElementById('stat-bindings'))) el.textContent = data.bindings || 0;
          if ((el = document.getElementById('stat-unbinds'))) el.textContent = (data.unbinds || 0) + ' unbinds';
          if ((el = document.getElementById('stat-sync'))) el.textContent = (data.sync_success || 0) + ' / ' + (data.sync_total || 0);
          if ((el = document.getElementById('stat-sync-rate'))) el.textContent = (data.sync_success_rate || 0) + '% success';

          // Breakdown
          var bd = data.image_command_breakdown || [];
          var bdChart = document.getElementById('breakdown-chart');
          var bdTitle = document.getElementById('breakdown-title');
          if (bdTitle) bdTitle.textContent = 'Image calls breakdown (' + (isToday ? 'today' : date) + ')';
          if (bdChart) {
            if (bd.length === 0) {
              bdChart.innerHTML = '<div style="opacity:0.5;font-size:13px;">No data</div>';
            } else {
              var cmdMax = bd[0].count || 1;
              var bhtml = '';
              for (var j = 0; j < bd.length; j++) {
                var row = bd[j];
                var label = _cmdLabels[row.command] || row.command;
                var pct = (row.count / cmdMax * 100).toFixed(1);
                bhtml += '<div style="display:flex;align-items:center;gap:10px;">' +
                  '<div style="min-width:130px;font-size:13px;">' + label + '</div>' +
                  '<div style="flex:1;height:14px;background:var(--border-color);opacity:0.3;border-radius:4px;overflow:hidden;">' +
                  '<div style="height:100%;background:var(--accent-color);width:' + pct + '%;border-radius:4px;"></div></div>' +
                  '<div style="min-width:50px;text-align:right;font-weight:600;font-size:13px;">' + row.count + '</div></div>';
              }
              bdChart.innerHTML = bhtml;
            }
          }
        })
        .catch(function(err) { showToast('Failed to load data: ' + err); });
    }

    function initStatsInteractions() {
      // DAU chart: hover tooltip + click to load date
      var svg = document.getElementById('dau-svg');
      var tooltip = document.getElementById('dau-tooltip');
      if (svg && tooltip) {
        svg.querySelectorAll('.dau-dot').forEach(function(dot) {
          dot.addEventListener('mouseenter', function() {
            var rect = svg.parentElement.getBoundingClientRect();
            var dotRect = dot.getBoundingClientRect();
            tooltip.textContent = this.dataset.date + ' · DAU ' + this.dataset.dau;
            tooltip.style.display = 'block';
            var tx = dotRect.left - rect.left + dotRect.width / 2 - tooltip.offsetWidth / 2;
            var ty = dotRect.top - rect.top - tooltip.offsetHeight - 8;
            tooltip.style.left = Math.max(0, Math.min(tx, rect.width - tooltip.offsetWidth)) + 'px';
            tooltip.style.top = ty + 'px';
            this.setAttribute('r', '6');
          });
          dot.addEventListener('mouseleave', function() {
            tooltip.style.display = 'none';
            this.setAttribute('r', '3.5');
          });
          dot.addEventListener('click', function() {
            var fullDate = this.dataset.fullDate;
            var dateInput = document.getElementById('hourly-date');
            if (dateInput) {
              dateInput.value = fullDate;
              _loadDateData(fullDate);
            }
          });
        });
      }

      // Hourly date picker
      var dateInput = document.getElementById('hourly-date');
      if (dateInput) {
        var today = new Date().getFullYear() + '-' + String(new Date().getMonth()+1).padStart(2,'0') + '-' + String(new Date().getDate()).padStart(2,'0');
        dateInput.value = today;
        dateInput.max = today;
        dateInput.addEventListener('change', function() { _loadDateData(this.value); });
        // 页面加载时立即用本地日期刷新，避免 DB 时区与浏览器时区不一致
        _loadDateData(today);
      }
    }

    initStatsInteractions();

    let dxdataAuditReport = null;
    let dxdataAuditTimer = null;
    let dxdataAuditPage = 0;
    const dxdataAuditNames = {order_conflict: '定数排序冲突', version_mismatch: '版本不符'};

    async function startDXDataAudit() {
      const id = document.getElementById('dxdata-audit-id');
      const password = document.getElementById('dxdata-audit-password');
      const status = document.getElementById('dxdata-audit-status');
      if (!id.value.trim() || !password.value) {
        status.textContent = '数据更新与官网检查是两个步骤。请输入 SEGA ID 和密码，然后点击「检查当前数据」。';
        document.getElementById('dxdata-audit-setup').open = true;
        document.getElementById('dxdata-audit-panel').scrollIntoView({block: 'center'});
        (id.value.trim() ? password : id).focus();
        return;
      }
      const button = document.getElementById('dxdata-audit-start');
      button.disabled = true;
      try {
        const body = JSON.stringify({sega_id: id.value.trim(), password: password.value,
          aime: Number(document.getElementById('dxdata-audit-aime').value)});
        password.value = '';
        const response = await fetch('/admin/dxdata_audit', {
          method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken}, body
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || '无法开始检查');
        dxdataAuditPage = 0;
        await loadDXDataAudit();
      } catch (error) {
        status.textContent = error.message;
        button.disabled = false;
      }
    }

    async function loadDXDataAudit() {
      clearTimeout(dxdataAuditTimer);
      try {
        const response = await fetch('/admin/dxdata_audit');
        if (!response.ok) throw new Error('无法读取检查结果');
        dxdataAuditReport = await response.json();
        renderDXDataAudit();
        if (dxdataAuditReport.status === 'running') dxdataAuditTimer = setTimeout(loadDXDataAudit, 2500);
      } catch (error) {
        document.getElementById('dxdata-audit-status').textContent = error.message;
      }
    }

    async function approveDXDataVersions() {
      const report = dxdataAuditReport;
      const region = document.getElementById('dxdata-audit-region').value;
      const button = document.getElementById('dxdata-audit-approve-versions');
      if (!report || report.stale || report.status !== 'complete' || button.disabled) return;
      button.disabled = true;
      button.textContent = '保存中…';
      try {
        const response = await fetch('/admin/dxdata_audit/versions', {
          method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken},
          body: JSON.stringify({revision: report.revision, region})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || '保存失败');
        dxdataAuditReport = data.report;
        dxdataAuditPage = 0;
        showToast(`${region.toUpperCase()} 版本修正已全部保存`, 'success');
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        renderDXDataAudit();
      }
    }

    function renderDXDataAudit() {
      const report = dxdataAuditReport;
      if (!report) return;
      const running = report.status === 'running';
      document.getElementById('dxdata-audit-start').disabled = running;
      document.getElementById('update-dxdata-btn').disabled = running;
      const stateNames = {pending: '等待', running: '检查中', complete: '完成', failed: '失败'};
      document.getElementById('dxdata-audit-status').textContent = report.status === 'idle' ? '尚未检查' :
        ['jp', 'intl'].map(r => `${r.toUpperCase()}: ${stateNames[report.regions?.[r]?.status] || '未检查'}`).join(' · ') +
        (report.stale ? ' · 数据已变化，请重新检查后保存。' : '');
      const region = document.getElementById('dxdata-audit-region').value;
      const result = report.regions?.[region];
      const approve = document.getElementById('dxdata-audit-approve-versions');
      approve.hidden = true;
      const container = document.getElementById('dxdata-audit-results');
      const pagination = document.getElementById('dxdata-audit-pagination');
      container.replaceChildren(); pagination.replaceChildren();
      function text(parent, tag, value) {
        const node = document.createElement(tag); node.textContent = value; parent.append(node); return node;
      }
      if (!result || result.status !== 'complete') {
        text(container, 'p', result?.error || (running ? '正在抓取官网列表，请稍候…' : '此版本暂无结果'));
        return;
      }
      const summary = text(container, 'div', `${result.summary.issues} 项待核对 · ${result.summary.charts} 个谱面 · 检查于 ${result.fetched_at ? new Date(result.fetched_at).toLocaleString() : '—'}`);
      summary.className = 'audit-summary';
      const filter = document.getElementById('dxdata-audit-filter').value;
      const issues = result.issues.map((issue, index) => ({issue, index})).filter(({issue}) => issue.kind === (filter === 'version' ? 'version_mismatch' : 'order_conflict'));
      approve.hidden = filter !== 'version' || !issues.length;
      approve.disabled = report.status !== 'complete' || report.stale;
      approve.textContent = `一键通过全部版本修正（${issues.length}）`;
      const pages = Math.max(1, Math.ceil(issues.length / 20));
      dxdataAuditPage = Math.min(dxdataAuditPage, pages - 1);
      if (!issues.length) text(container, 'p', '当前筛选没有问题。');
      for (const {issue, index} of issues.slice(dxdataAuditPage * 20, (dxdataAuditPage + 1) * 20)) {
        const isVersion = issue.kind === 'version_mismatch';
        let charts = isVersion ? [issue.chart] : (issue.correction_candidates ?? [issue.before, issue.after].filter(chart => {
          const inference = chart?.inference;
          return inference && ['exact', 'range'].includes(inference.status) &&
            (chart.internalLevelValue < inference.min || chart.internalLevelValue > inference.max);
        }));
        const needsManualReview = !isVersion && !charts.length;
        if (needsManualReview) charts = [issue.before, issue.after];
        for (const chart of charts.filter(Boolean)) {
          const card = document.createElement('article'); card.className = 'section audit-compact-card'; container.append(card);
          const title = chart.title.trim() || '（全角空格曲名）';
          text(card, 'strong', title).className = 'audit-compact-title';
          text(card, 'small', `${region.toUpperCase()} · ${chart.type.toUpperCase()} · ${chart.difficulty.toUpperCase()}`).className = 'audit-compact-meta';
          const inference = chart.inference;
          const manual = !isVersion && (needsManualReview || !inference || inference.status === 'level_only');
          const current = isVersion ? (chart.version || '未知') : chart.internalLevelValue;
          const predicted = isVersion ? issue.official_version : manual ? '无法确定' : inference.min === inference.max ?
            inference.min.toFixed(1) : `${inference.min.toFixed(1)}～${inference.max.toFixed(1)}`;
          const comparison = document.createElement('div'); comparison.className = 'audit-compact-values'; card.append(comparison);
          const oldValue = document.createElement('div'); comparison.append(oldValue);
          text(oldValue, 'small', isVersion ? '文件内版本' : '文件内定数'); text(oldValue, 'strong', current);
          text(comparison, 'span', '→').className = 'audit-compact-arrow';
          const newValue = document.createElement('div'); comparison.append(newValue);
          text(newValue, 'small', isVersion ? '官网版本' : '推测定数'); text(newValue, 'strong', predicted);
          const form = document.createElement('form'); form.className = 'audit-compact-actions'; card.append(form);
          let chosenValue = isVersion ? issue.official_version : manual ? '' : inference.min.toFixed(1);
          if (manual) {
            const input = document.createElement('input');
            input.type = 'number'; input.step = '0.1'; input.min = '1'; input.max = '15.9'; input.required = true;
            input.className = 'form-input'; input.placeholder = '手动输入修正定数';
            input.setAttribute('aria-label', `${title} 修正值`);
            input.oninput = () => { chosenValue = input.value; };
            form.append(input);
          } else if (!isVersion && inference.min !== inference.max) {
            const select = document.createElement('select');
            select.setAttribute('aria-label', `${title} 修正值`); select.required = true;
            select.add(new Option('选择区间内的值', ''));
            for (let value = Math.round(inference.min * 10); value <= Math.round(inference.max * 10); value++) {
              select.add(new Option((value / 10).toFixed(1), (value / 10).toFixed(1)));
            }
            chosenValue = '';
            select.onchange = () => { chosenValue = select.value; };
            form.append(select);
          }
          const prompt = text(form, 'span', '是否修改？');
          const yes = document.createElement('button'); yes.type = 'submit'; yes.className = 'btn btn-success'; yes.textContent = '修改';
          const no = document.createElement('button'); no.type = 'button'; no.className = 'btn'; no.textContent = '不修改';
          yes.disabled = running || report.stale || !chart.song_id;
          form.append(yes, no);
          no.onclick = () => {
            const skipped = card.classList.toggle('audit-skipped');
            prompt.textContent = skipped ? '已跳过' : '是否修改？';
            yes.disabled = skipped || running || report.stale || !chart.song_id;
            no.textContent = skipped ? '重新选择' : '不修改';
          };
          form.onsubmit = async event => {
            event.preventDefault();
            if (!chosenValue) return;
            yes.disabled = true; no.disabled = true; yes.textContent = '保存中…';
            try {
              const response = await fetch('/admin/dxdata_audit/correction', {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': window.JIETNG_ADMIN_CONFIG.csrfToken},
                body: JSON.stringify({revision: report.revision, region, issue_index: index, song_id: chart.song_id,
                  difficulty: chart.difficulty, field: isVersion ? 'version' : 'internalLevelValue', value: chosenValue})
              });
              const data = await response.json();
              if (!response.ok) throw new Error(data.message || '保存失败');
              dxdataAuditReport = data.report; renderDXDataAudit(); showToast('已修改', 'success');
            } catch (error) {
              showToast(error.message, 'error'); yes.disabled = false; no.disabled = false; yes.textContent = '修改';
            }
          };
        }
      }
      for (const [label, step] of [['上一页', -1], ['下一页', 1]]) {
        const button = document.createElement('button'); button.className = 'btn'; button.textContent = label;
        button.disabled = dxdataAuditPage + step < 0 || dxdataAuditPage + step >= pages;
        button.onclick = () => { dxdataAuditPage += step; renderDXDataAudit(); };
        pagination.append(button);
      }
      text(pagination, 'span', `${dxdataAuditPage + 1} / ${pages} 页`);
    }
