---
layout: page
---

<script setup>
import { ref, computed, onMounted } from 'vue'

const segaid = ref('')
const password = ref('')
const ver = ref('jp')
const aime = ref('0')
const loading = ref(false)
const error = ref('')
const imageUrl = ref('')
const timezone = -new Date().getTimezoneOffset() / 60

const CMD_INFO = {
  sun50: { cmd: 's50', label: 's50 — SSS / SSS+ Near-miss 50', title: 'SUN 50' },
  best50: { cmd: 'b50',      label: 'b50 — Best 50',            title: 'BEST 50' },
  best40: { cmd: 'b40',      label: 'b40 — Best 40',            title: 'BEST 40' },
  best35: { cmd: 'b35',      label: 'b35 — Best 35',            title: 'BEST 35' },
  best15: { cmd: 'b15',      label: 'b15 — Best 15',            title: 'BEST 15' },
  allb35: { cmd: 'ab35',     label: 'ab35 — All Best 35',       title: 'ALL BEST 35' },
  allb50: { cmd: 'ab50',     label: 'ab50 — All Best 50',       title: 'ALL BEST 50' },
  apb50:  { cmd: 'apb50',    label: 'apb50 — AP Best 50 ',      title: 'AP BEST 50' },
  fdxb50: { cmd: 'fdxb50',   label: 'fdxb50 — FDX Best 50',     title: 'FDX BEST 50' },
  idlb50: { cmd: 'idealb50', label: 'idealb50 — Ideal Best 50', title: 'IDEAL BEST 50' },
}

const cmdType = ref('best50')
const showParams = ref(false)

// Parameters
const paramLvMin   = ref('')
const paramLvMax   = ref('')
const paramRaMin   = ref('')
const paramRaMax   = ref('')
const paramStarMin = ref('')
const paramStarMax = ref('')
const paramScrMin  = ref('')
const paramScrMax  = ref('')
const paramDxMin   = ref('')
const paramDxMax   = ref('')
const paramDiff    = ref([])
const paramType    = ref('')
const paramVer     = ref('')
const paramNext    = ref(false)
const paramPage    = ref('')

const DIFFS = ['bas', 'adv', 'exp', 'mas', 'rem']

const paramsString = computed(() => {
  const parts = []
  const lvMin = String(paramLvMin.value).trim()
  const lvMax = String(paramLvMax.value).trim()
  if (lvMin) parts.push(lvMax ? `-lv ${lvMin} ${lvMax}` : `-lv ${lvMin}`)

  const raMin = String(paramRaMin.value).trim()
  const raMax = String(paramRaMax.value).trim()
  if (raMin) parts.push(raMax ? `-ra ${raMin} ${raMax}` : `-ra ${raMin}`)

  const starMin = String(paramStarMin.value).trim()
  const starMax = String(paramStarMax.value).trim()
  if (starMin) parts.push(starMax ? `-star ${starMin} ${starMax}` : `-star ${starMin}`)

  const scrMin = String(paramScrMin.value).trim()
  const scrMax = String(paramScrMax.value).trim()
  if (scrMin) parts.push(scrMax ? `-scr ${scrMin} ${scrMax}` : `-scr ${scrMin}`)

  const dxMin = String(paramDxMin.value).trim()
  const dxMax = String(paramDxMax.value).trim()
  if (dxMin) parts.push(dxMax ? `-dx ${dxMin} ${dxMax}` : `-dx ${dxMin}`)

  if (paramDiff.value.length > 0) parts.push(`-diff ${paramDiff.value.join(' ')}`)

  if (paramType.value) parts.push(`-type ${paramType.value}`)

  const ver = String(paramVer.value).trim()
  if (ver) parts.push(`-ver ${ver}`)

  if (paramNext.value) parts.push('-next')

  const page = parseInt(String(paramPage.value))
  if (page > 1) parts.push(`-page ${page}`)

  return parts.join(' ')
})

const commandPreview = computed(() => {
  const info = CMD_INFO[cmdType.value] || CMD_INFO.best50
  return paramsString.value ? `${info.cmd} ${paramsString.value}` : info.cmd
})

const btnLabel = computed(() => {
  const info = CMD_INFO[cmdType.value] || CMD_INFO.best50
  return `生成 ${info.title}`
})

function toggleDiff(d) {
  if (loading.value) return
  const idx = paramDiff.value.indexOf(d)
  if (idx === -1) paramDiff.value.push(d)
  else paramDiff.value.splice(idx, 1)
}

async function generate() {
  if (!segaid.value || !password.value) return
  error.value = ''
  if (imageUrl.value) { URL.revokeObjectURL(imageUrl.value); imageUrl.value = '' }
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('segaid', segaid.value)
    fd.append('password', password.value)
    fd.append('ver', ver.value)
    fd.append('aime', aime.value)
    fd.append('timezone', timezone)
    fd.append('cmd_type', cmdType.value)
    fd.append('params', paramsString.value)
    writeCookie()
    const res = await fetch('https://jietng-endpoint.matsuk1.com/linebot/demo', { method: 'POST', body: fd })
    if (res.ok) {
      const blob = await res.blob()
      imageUrl.value = URL.createObjectURL(blob)
    } else {
      const data = await res.json().catch(() => ({}))
      error.value = data.error || '生成失败，请重试。'
    }
  } catch {
    error.value = '网络错误，请检查网络连接后重试。'
  } finally {
    loading.value = false
  }
}

function reset() {
  if (imageUrl.value) { URL.revokeObjectURL(imageUrl.value); imageUrl.value = '' }
  error.value = ''
}

const saveCreds = ref(false)

// Load from cookie on mount
onMounted(() => {
  const m = document.cookie.match(/(?:^|;\s*)demo_creds=([^;]+)/)
  if (m) {
    try {
      const d = JSON.parse(decodeURIComponent(m[1]))
      if (d.segaid) segaid.value = d.segaid
      if (d.password) password.value = d.password
      if (d.ver) ver.value = d.ver
      if (d.aime !== undefined) aime.value = String(d.aime)
      saveCreds.value = true
    } catch {}
  }
})

function onSaveCredsChange() {
  if (saveCreds.value) {
    writeCookie()
  } else {
    document.cookie = 'demo_creds=; max-age=0; path=/'
  }
}

function writeCookie() {
  if (!saveCreds.value) return
  const d = JSON.stringify({ segaid: segaid.value, password: password.value, ver: ver.value, aime: aime.value })
  document.cookie = 'demo_creds=' + encodeURIComponent(d) + '; max-age=7776000; path=/; SameSite=Strict'
}
</script>

<div class="demo-page">
  <div class="demo-hero">
    <h1>在线体验</h1>
    <p>无需 LINE，直接输入 SEGA 账号即可生成你的 Best 系列成绩图。</p>
  </div>

  <div class="demo-card" v-if="!imageUrl">
    <form @submit.prevent="generate">
      <div class="field">
        <label for="segaid">SEGA ID</label>
        <input id="segaid" v-model="segaid" type="text" placeholder="你的 SEGA ID" autocomplete="username" required :disabled="loading" />
      </div>
      <div class="field">
        <label for="password">密码</label>
        <input id="password" v-model="password" type="password" placeholder="你的 SEGA 密码" autocomplete="current-password" required :disabled="loading" />
      </div>
      <div class="field">
        <label for="ver">服务器</label>
        <select id="ver" v-model="ver" :disabled="loading">
          <option value="jp">日服 - maimaidx.jp</option>
          <option value="intl">国际服 - maimaidx-eng.com</option>
        </select>
      </div>
      <div class="field">
        <label for="aime">Aime 卡槽</label>
        <select id="aime" v-model="aime" :disabled="loading">
          <option value="0">No.1</option>
          <option value="1">No.2</option>
          <option value="2">No.3</option>
        </select>
      </div>
      <div class="field">
        <label for="cmd-type">命令</label>
        <select id="cmd-type" v-model="cmdType" :disabled="loading">
          <option v-for="(info, key) in CMD_INFO" :key="key" :value="key">{{ info.label }}</option>
        </select>
      </div>
      <div class="params-section">
        <button type="button" class="params-toggle" @click="showParams = !showParams" :disabled="loading"><span>过滤参数（可选）</span><span class="params-arrow" :class="{ 'params-arrow--open': showParams }">&#9656;</span></button>
        <div v-show="showParams" class="params-body">
        <div class="param-field">
          <label>难度</label>
          <div class="diff-group" :class="{ 'diff-group--disabled': loading }">
            <button
              v-for="d in DIFFS" :key="d"
              type="button"
              class="diff-chip"
              :class="paramDiff.includes(d) ? 'diff-chip--' + d : ''"
              @click="toggleDiff(d)"
            >{{ d.toUpperCase() }}</button>
          </div>
        </div>
        <div class="param-field">
          <label>定数</label>
          <div class="range-inputs">
            <input type="number" v-model="paramLvMin" placeholder="最小（如 14）" step="0.1" min="1" max="15" :disabled="loading" />
            <span class="range-sep">~</span>
            <input type="number" v-model="paramLvMax" placeholder="最大（如 14.9）" step="0.1" min="1" max="15" :disabled="loading" />
          </div>
        </div>
        <div class="param-field">
          <label>Rating</label>
          <div class="range-inputs">
            <input type="number" v-model="paramRaMin" placeholder="最小（如 301）" step="1" min="0" :disabled="loading" />
            <span class="range-sep">~</span>
            <input type="number" v-model="paramRaMax" placeholder="最大（如 312）" step="1" min="0" :disabled="loading" />
          </div>
        </div>
        <div class="param-field">
          <label>DX 星数</label>
          <div class="range-inputs">
            <input type="number" v-model="paramStarMin" placeholder="最小（1~5）" step="1" min="1" max="5" :disabled="loading" />
            <span class="range-sep">~</span>
            <input type="number" v-model="paramStarMax" placeholder="最大（可选）" step="1" min="1" max="5" :disabled="loading" />
          </div>
        </div>
        <div class="param-field">
          <label>达成率 %</label>
          <div class="range-inputs">
            <input type="number" v-model="paramScrMin" placeholder="最小（如 99）" step="0.0001" min="0" max="101" :disabled="loading" />
            <span class="range-sep">~</span>
            <input type="number" v-model="paramScrMax" placeholder="最大（可选）" step="0.0001" min="0" max="101" :disabled="loading" />
          </div>
        </div>
        <div class="param-field">
          <label>DX Score %</label>
          <div class="range-inputs">
            <input type="number" v-model="paramDxMin" placeholder="最小（如 90）" step="1" min="0" max="100" :disabled="loading" />
            <span class="range-sep">~</span>
            <input type="number" v-model="paramDxMax" placeholder="最大（可选）" step="1" min="0" max="100" :disabled="loading" />
          </div>
        </div>
        <div class="param-field param-field--inline">
          <label>谱面类型</label>
          <select class="type-select" v-model="paramType" :disabled="loading">
            <option value="">全部</option>
            <option value="dx">DX 谱面</option>
            <option value="std">标准谱面</option>
          </select>
        </div>
        <div class="param-field">
          <label>版本</label>
          <input class="ver-input" type="text" v-model="paramVer" placeholder="如 splash+ (plus → +)" :disabled="loading" />
        </div>
        <div class="param-field param-field--inline">
          <label>Next 版本分组</label>
          <label class="next-toggle"><input type="checkbox" v-model="paramNext" :disabled="loading" />启用</label>
        </div>
        <div class="param-field param-field--inline">
          <label>页码</label>
          <input class="page-input" type="number" v-model="paramPage" placeholder="默认第 1 页" min="1" max="99" :disabled="loading" />
        </div>
        </div>
      </div>
      <div class="cmd-preview">
        <span class="cmd-prefix">命令预览：</span><code>{{ commandPreview }}</code>
      </div>
      <button type="submit" :disabled="loading" class="btn-primary">
        <span v-if="loading" class="spinner"></span>
        <span>{{ loading ? '生成中，请稍候…' : btnLabel }}</span>
      </button>
      <p v-if="error" class="error-msg">{{ error }}</p>
    </form>
    <label class="save-creds"><input type="checkbox" v-model="saveCreds" @change="onSaveCredsChange" />记住账号信息</label>
    <p class="notice">{{ saveCreds ? '你的账号信息会发送到 JiETNG 后端用于本次生成，并额外保存在本浏览器 Cookie 中方便下次填写；不会作为绑定账号保存。本服务由个人运营，与 SEGA 官方无关。' : '你的账号信息会发送到 JiETNG 后端用于本次生成，不会作为绑定账号保存。本服务由个人运营，与 SEGA 官方无关。' }}</p>
  </div>

  <div class="demo-card result-card" v-if="imageUrl">
    <img :src="imageUrl" alt="成绩图" class="result-img" />
    <div class="result-actions">
      <a :href="imageUrl" download="result.jpg" class="btn-primary">保存图片</a>
      <button @click="reset" class="btn-secondary">重新生成</button>
    </div>
  </div>
</div>

<style>
.demo-page {
  max-width: 520px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}

.demo-hero {
  text-align: center;
  margin-bottom: 32px;
}

.demo-hero h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  margin-bottom: 8px;
}

.demo-hero p {
  font-size: 1rem;
  color: var(--vp-c-text-2);
}

.demo-card {
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 32px;
}

.field {
  margin-bottom: 20px;
}

.field label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  margin-bottom: 8px;
}

.field input,
.field select {
  width: 100%;
  padding: 10px 14px;
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  font-size: 16px;
  color: var(--vp-c-text-1);
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.field input:disabled,
.field select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── 参数面板 ── */
.params-section {
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.params-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  color: var(--vp-c-text-3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: inherit;
  line-height: 1;
}

.params-toggle:hover {
  color: var(--vp-c-text-2);
}

.params-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.params-arrow {
  transition: transform 0.2s;
  font-size: 12px;
}

.params-arrow--open {
  transform: rotate(90deg);
}

.params-body {
  margin-top: 14px;
}

.param-field {
  margin-bottom: 12px;
}

.param-field:last-child {
  margin-bottom: 0;
}

.param-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--vp-c-text-2);
  margin-bottom: 6px;
}

.param-field--inline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.param-field--inline label {
  margin-bottom: 0;
  white-space: nowrap;
}

/* 难度选择器 */
.diff-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.diff-group--disabled {
  opacity: 0.5;
  pointer-events: none;
}

.diff-chip {
  padding: 4px 11px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  color: var(--vp-c-text-2);
  background: transparent;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  line-height: 1.6;
}

.diff-chip:hover {
  border-color: var(--vp-c-text-3);
  color: var(--vp-c-text-1);
}

.diff-chip:focus {
  outline: none;
}

.diff-chip:active {
  transform: scale(0.95);
}

.diff-chip--bas { background: #75b520; border-color: #75b520; color: #fff; }
.diff-chip--adv { background: #efa508; border-color: #efa508; color: #fff; }
.diff-chip--exp { background: #cc4d59; border-color: #cc4d59; color: #fff; }
.diff-chip--mas { background: #9f51dc; border-color: #9f51dc; color: #fff; }
.diff-chip--rem { background: #e9d4f3; border-color: #e9d4f3; color: #72148d; }

.diff-chip--bas:hover { background: #689e1c; border-color: #689e1c; }
.diff-chip--adv:hover { background: #d99407; border-color: #d99407; }
.diff-chip--exp:hover { background: #b8444f; border-color: #b8444f; }
.diff-chip--mas:hover { background: #8e48c5; border-color: #8e48c5; }
.diff-chip--rem:hover { background: #d4bedb; border-color: #d4bedb; }

/* 范围输入 */
.range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.range-inputs input,
.page-input {
  padding: 8px 10px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  font-size: 16px;
  color: var(--vp-c-text-1);
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.range-inputs input {
  flex: 1;
  min-width: 0;
}

.range-inputs input:focus,
.page-input:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.range-inputs input:disabled,
.page-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.page-input {
  width: 130px;
}

.next-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 400;
  color: var(--vp-c-text-1);
  cursor: pointer;
  user-select: none;
}

.next-toggle input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: var(--vp-c-brand-1);
  cursor: pointer;
}

.type-select {
  padding: 8px 10px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  font-size: 16px;
  color: var(--vp-c-text-1);
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
  cursor: pointer;
}

.type-select:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.type-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ver-input {
  width: 100%;
  padding: 8px 10px;
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  font-size: 16px;
  color: var(--vp-c-text-1);
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.ver-input:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.ver-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.range-sep {
  color: var(--vp-c-text-3);
  flex-shrink: 0;
  font-size: 13px;
}

/* 命令预览 */
.cmd-preview {
  padding: 9px 14px;
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--vp-c-text-2);
  word-break: break-all;
}

.cmd-prefix {
  color: var(--vp-c-text-3);
}

.cmd-preview code {
  color: var(--vp-c-brand-1);
  font-family: monospace;
  font-weight: 600;
}

/* ── 按钮 ── */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  background: var(--vp-c-brand-1);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.2s;
  text-decoration: none;
  margin-top: 4px;
  box-sizing: border-box;
  text-align: center;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  flex: 1;
  padding: 11px;
  background: transparent;
  color: var(--vp-c-text-2);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-msg {
  margin-top: 12px;
  font-size: 14px;
  color: var(--vp-c-danger-1, #f43f5e);
  line-height: 1.5;
}

.save-creds {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--vp-c-text-2);
  cursor: pointer;
  user-select: none;
}

.save-creds input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: var(--vp-c-brand-1);
  cursor: pointer;
  flex-shrink: 0;
}

.notice {
  margin-top: 20px;
  font-size: 12px;
  color: var(--vp-c-text-3);
  line-height: 1.6;
  text-align: center;
}

.result-card {
  text-align: center;
}

.result-img {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 16px;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-actions .btn-primary {
  flex: 1;
  margin-top: 0;
}
</style>
