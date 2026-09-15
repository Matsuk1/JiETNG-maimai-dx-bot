'use strict';
const $ = id => document.getElementById(id);
let cases = [], kind = '', defaults = '', imageURL = '', naturalWidth = 0;
let timer, serial = 0, pending = false, rendering = false, revision = '';
const storageKey = id => `jietng-image-lab:${id}`;
const readDraft = id => { try { return localStorage.getItem(storageKey(id)); } catch { return null; } };
function saveDraft() { try { localStorage.setItem(storageKey(kind), $('editor').value); } catch {} }
function setStatus(text, state = '') { $('status').textContent = text; $('status-dot').className = `dot ${state}`; }
function showError(text) { $('error').textContent = text; $('error').hidden = !text; }
function dirtyState() { $('draft-state').textContent = $('editor').value === defaults ? '示例原始数据' : '草稿已保存在此浏览器'; }
function parseData() {
  const data = JSON.parse($('editor').value);
  if (!data || Array.isArray(data) || typeof data !== 'object') throw Error('根节点必须是 JSON 对象');
  return data;
}
function zoom() {
  if (!naturalWidth) return;
  const factor = $('zoom').value === 'fit' ? Math.min(2, Math.max(.1, ($('viewport').clientWidth - 70) / naturalWidth)) : Number($('zoom').value);
  $('preview').style.width = `${Math.round(naturalWidth * factor)}px`;
}
function download(url, name) { const link = document.createElement('a'); link.href = url; link.download = name; link.click(); }
function quickFields(data) {
  $('quick-fields').replaceChildren();
  const object = data.record || data.user || data.song || data.cover;
  if (!object) return;
  const fields = data.user ? [['name','昵称'],['rating','Rating'],['trophy_content','称号']] :
    [['name' in object ? 'name' : 'song_title' in object ? 'song_title' : 'title','名称'],['score','达成率'],['internalLevelValue','定数'],['ra','Rating'],['difficulty','难度']];
  for (const [key,label] of fields) {
    if (!(key in object)) continue;
    const wrapper = document.createElement('label'); wrapper.className = 'quick-field' + (['name','title','song_title','trophy_content'].includes(key) ? ' wide' : '');
    const caption = document.createElement('span'); caption.textContent = label; wrapper.append(caption);
    const input = document.createElement(key === 'difficulty' ? 'select' : 'input');
    if (key === 'difficulty') for (const value of ['basic','advanced','expert','master','remaster','utage']) { const option = document.createElement('option'); option.value = value; option.textContent = value; input.append(option); }
    input.value = object[key]; input.setAttribute('aria-label', label); input.dataset.field = key;
    input.addEventListener('input', () => {
      try {
        const updated = parseData(), target = updated.record || updated.user || updated.song || updated.cover;
        if (typeof target[key] === 'number') {
          if (input.value.trim() === '' || !Number.isFinite(Number(input.value))) return;
          target[key] = Number(input.value);
        } else target[key] = input.value;
        $('editor').value = JSON.stringify(updated, null, 2); changed(false);
      } catch (error) { showError(error.message); }
    });
    wrapper.append(input); $('quick-fields').append(wrapper);
  }
}
function changed(rebuild = true) {
  serial++; saveDraft(); dirtyState();
  try { const data = parseData(); showError(''); if (rebuild) quickFields(data); }
  catch (error) { showError(`JSON 格式错误：${error.message}`); setStatus('等待修正数据', 'bad'); clearTimeout(timer); return; }
  if ($('auto').checked) schedule(); else setStatus('有未渲染的修改');
}
function schedule(immediate = false) {
  clearTimeout(timer);
  timer = setTimeout(() => { pending = true; renderLatest(); }, immediate ? 0 : 450);
}
async function renderLatest() {
  if (rendering || !pending || !kind) return;
  let data;
  try { data = parseData(); } catch (error) { showError(`JSON 格式错误：${error.message}`); pending = false; return; }
  pending = false; rendering = true;
  const ticket = serial, selected = kind;
  setStatus('正在渲染…', 'busy');
  try {
    const response = await fetch(`/api/render/${selected}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    if (!response.ok) { let result; try { result = await response.json(); } catch {} throw Error(result?.error || `渲染失败（HTTP ${response.status}）`); }
    const blob = await response.blob();
    if (ticket !== serial || selected !== kind) return;
    const url = URL.createObjectURL(blob), candidate = new Image(); candidate.src = url;
    try { await candidate.decode(); } catch (error) { URL.revokeObjectURL(url); throw error; }
    if (ticket !== serial || selected !== kind) { URL.revokeObjectURL(url); return; }
    if (imageURL) URL.revokeObjectURL(imageURL);
    imageURL = url; naturalWidth = Number(response.headers.get('X-Image-Width')) || candidate.width;
    $('preview').src = url; $('preview').hidden = false; $('empty').hidden = true; $('download').disabled = false;
    $('dimensions').textContent = `${naturalWidth} × ${response.headers.get('X-Image-Height')} px`;
    $('timing').textContent = `${response.headers.get('X-Render-Ms')} ms · Chromium`;
    zoom(); showError(''); setStatus('预览已更新');
  } catch (error) { if (ticket === serial) { showError(error.message); setStatus('渲染失败', 'bad'); } }
  finally { rendering = false; if (pending) renderLatest(); }
}
async function selectCase(id) {
  const ticket = ++serial; kind = id;
  try { localStorage.setItem('jietng-image-lab:selected', id); } catch {}
  for (const button of $('examples').children) { button.classList.toggle('active', button.dataset.id === id); button.setAttribute('aria-current', button.dataset.id === id ? 'true' : 'false'); }
  const item = cases.find(item => item.id === id);
  $('case-title').textContent = item.label; $('case-description').textContent = item.description; $('source-path').textContent = item.template;
  setStatus('读取示例…');
  try {
    const response = await fetch(`/api/examples/${id}`); if (!response.ok) throw Error('读取示例失败');
    const data = await response.json(); if (ticket !== serial) return;
    defaults = JSON.stringify(data, null, 2); $('editor').value = readDraft(id) ?? defaults;
    try { quickFields(parseData()); showError(''); } catch { $('editor').value = defaults; quickFields(data); }
    dirtyState(); schedule(true);
  } catch (error) { showError(error.message); setStatus('载入失败', 'bad'); }
}
$('editor').addEventListener('input', () => changed());
$('refresh').addEventListener('click', () => { serial++; schedule(true); });
$('auto').addEventListener('change', () => { if ($('auto').checked) schedule(true); else { clearTimeout(timer); pending = false; } });
$('format').addEventListener('click', () => { try { $('editor').value = JSON.stringify(parseData(),null,2); changed(); } catch (error) { showError(error.message); } });
$('reset').addEventListener('click', () => { $('editor').value = defaults; changed(); schedule(true); });
$('zoom').addEventListener('change', zoom);
$('backdrop').addEventListener('change', () => { $('viewport').className = `viewport ${$('backdrop').value}`; });
$('download').addEventListener('click', () => { if (imageURL) download(imageURL, `${kind}.png`); });
$('export').addEventListener('click', () => { try { const url = URL.createObjectURL(new Blob([JSON.stringify(parseData(),null,2)],{type:'application/json'})); download(url,`${kind}.json`); setTimeout(() => URL.revokeObjectURL(url),1000); } catch (error) { showError(error.message); } });
document.addEventListener('keydown', event => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); serial++; schedule(true); } });
new ResizeObserver(zoom).observe($('viewport'));
async function watch() {
  try {
    if (document.hidden) return;
    const response = await fetch('/api/revision'); if (!response.ok) throw Error(); const result = await response.json();
    if (revision && revision !== result.revision) {
      $('watcher').textContent = '检测到模板 / 示例更新';
      if ($('editor').value === defaults) {
        const fixture = await (await fetch(`/api/examples/${kind}`)).json();
        defaults = JSON.stringify(fixture,null,2); $('editor').value = defaults; quickFields(fixture); dirtyState();
      }
      serial++; if ($('auto').checked) schedule(true); else setStatus('模板已更新，等待渲染');
    } else $('watcher').textContent = '模板监听中';
    revision = result.revision;
  } catch { $('watcher').textContent = '连接中断，正在重试…'; }
  finally { setTimeout(watch,1500); }
}
(async () => {
  try {
    const response = await fetch('/api/examples'); if (!response.ok) throw Error('无法连接本地调试服务'); cases = await response.json();
    $('case-count').textContent = cases.length;
    cases.forEach((item,index) => { const button = document.createElement('button'); button.className = 'case-button'; button.dataset.id = item.id;
      const number = document.createElement('span'); number.textContent = String(index+1).padStart(2,'0');
      const label = document.createElement('span'); label.textContent = item.label; button.append(number,label);
      button.addEventListener('click', () => selectCase(item.id)); $('examples').append(button); });
    let selected; try { selected = localStorage.getItem('jietng-image-lab:selected'); } catch {}
    await selectCase(cases.some(item => item.id === selected) ? selected : cases[0].id); watch();
  } catch (error) { showError(error.message); setStatus('连接失败','bad'); }
})();
