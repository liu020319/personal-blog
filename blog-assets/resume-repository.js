(function () {
  'use strict';

  const config = window.BLOG_DATA?.resume || {};
  const apiBase = String(config.api || './blog-api').replace(/\/$/, '');
  const tokenKey = 'xiaoliu-resume-admin-token';

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  async function request(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {
      cache: 'no-store',
      ...options,
      headers: { Accept: 'application/json', ...(options.headers || {}) }
    });
    const type = response.headers.get('content-type') || '';
    const payload = type.includes('application/json') ? await response.json() : {};
    if (!response.ok) throw new ApiError(payload.message || `请求失败（${response.status}）`, response.status);
    return payload;
  }

  function getToken() {
    return sessionStorage.getItem(tokenKey) || '';
  }

  function setToken(token) {
    if (token) sessionStorage.setItem(tokenKey, token);
    else sessionStorage.removeItem(tokenKey);
  }

  function adminHeaders() {
    return { Authorization: `Bearer ${getToken()}` };
  }

  function ensureDialogs() {
    if (document.getElementById('resume-auth-dialog')) return;
    document.body.insertAdjacentHTML('beforeend', `
      <dialog class="resume-dialog" id="resume-auth-dialog">
        <form class="resume-dialog-panel" id="resume-auth-form">
          <div class="resume-dialog-head"><div><p class="eyebrow">ADMIN ACCESS</p><h2>进入简历管理</h2></div><button class="dialog-close" type="button" data-close-dialog aria-label="关闭">×</button></div>
          <p class="dialog-help">输入服务器部署时生成的管理口令。口令只保存在当前浏览器会话，关闭页面后自动清除。</p>
          <label class="field-label">管理口令<input name="token" type="password" minlength="32" autocomplete="current-password" required placeholder="请输入管理口令" /></label>
          <p class="form-message" aria-live="polite"></p>
          <div class="dialog-actions"><button class="secondary-button" type="button" data-close-dialog>取消</button><button class="primary-button" type="submit">验证并进入</button></div>
        </form>
      </dialog>
      <dialog class="resume-dialog" id="resume-upload-dialog">
        <form class="resume-dialog-panel resume-upload-form" id="resume-upload-form">
          <div class="resume-dialog-head"><div><p class="eyebrow">NEW VERSION</p><h2>上传一份历史简历</h2></div><button class="dialog-close" type="button" data-close-dialog aria-label="关闭">×</button></div>
          <p class="dialog-help">上传后会立即公开展示。原始文件不会被修改，服务器使用随机文件名保存公开副本。</p>
          <div class="form-grid">
            <label class="field-label field-wide">PDF 文件<input name="file" type="file" accept="application/pdf,.pdf" required /></label>
            <label class="field-label">版本名称<input name="version" maxlength="40" required placeholder="例如：2025.06 · 毕业版" /></label>
            <label class="field-label">阶段名称<input name="stage" maxlength="60" required placeholder="例如：刚毕业阶段" /></label>
            <label class="field-label">版本日期<input name="date" type="date" required /></label>
            <label class="checkbox-label"><input name="current" type="checkbox" />设为当前公开简历</label>
            <label class="field-label field-wide">这一版发生了什么变化<textarea name="change" minlength="4" maxlength="300" rows="4" required placeholder="记录技能重点、项目表达或求职方向的变化"></textarea></label>
          </div>
          <label class="privacy-confirm"><input name="privacyConfirmed" type="checkbox" required /><span>我已确认 PDF 中不含真实姓名、私人电话/邮箱、身份证号、家庭地址、账号密码、内网地址、客户或公司保密信息，并同意立即公开。</span></label>
          <p class="form-message" aria-live="polite"></p>
          <div class="dialog-actions"><button class="secondary-button" type="button" data-close-dialog>取消</button><button class="primary-button" type="submit">确认上传并公开</button></div>
        </form>
      </dialog>`);

    document.querySelectorAll('[data-close-dialog]').forEach((button) => {
      button.addEventListener('click', () => button.closest('dialog')?.close());
    });
    document.querySelectorAll('.resume-dialog').forEach((dialog) => {
      dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    });
  }

  function showMessage(form, message, type = 'error') {
    const target = form.querySelector('.form-message');
    target.textContent = message;
    target.dataset.type = type;
  }

  async function verifyToken(token) {
    await request('/admin/check', { headers: { Authorization: `Bearer ${token}` } });
  }

  function login() {
    ensureDialogs();
    const dialog = document.getElementById('resume-auth-dialog');
    const form = document.getElementById('resume-auth-form');
    form.reset();
    showMessage(form, '', '');
    dialog.showModal();
    setTimeout(() => form.elements.token.focus(), 30);

    return new Promise((resolve, reject) => {
      const onClose = () => {
        cleanup();
        reject(new ApiError('已取消管理登录', 0));
      };
      const onSubmit = async (event) => {
        event.preventDefault();
        const button = form.querySelector('[type="submit"]');
        button.disabled = true;
        showMessage(form, '正在验证…', 'info');
        try {
          const token = form.elements.token.value.trim();
          await verifyToken(token);
          setToken(token);
          cleanup();
          dialog.close();
          resolve(token);
        } catch (error) {
          showMessage(form, error.message || '管理口令验证失败');
        } finally {
          button.disabled = false;
        }
      };
      const cleanup = () => {
        dialog.removeEventListener('close', onClose);
        form.removeEventListener('submit', onSubmit);
      };
      dialog.addEventListener('close', onClose, { once: true });
      form.addEventListener('submit', onSubmit);
    });
  }

  async function ensureAdmin() {
    const token = getToken();
    if (token) {
      try {
        await verifyToken(token);
        return token;
      } catch (error) {
        setToken('');
      }
    }
    return login();
  }

  async function list() {
    try {
      const payload = await request('/resumes');
      return { online: true, items: Array.isArray(payload.items) ? payload.items : [] };
    } catch (error) {
      return { online: false, items: Array.isArray(config.history) ? config.history : [], error: error.message };
    }
  }

  async function openUpload() {
    await ensureAdmin();
    ensureDialogs();
    const dialog = document.getElementById('resume-upload-dialog');
    const form = document.getElementById('resume-upload-form');
    form.reset();
    form.elements.date.value = new Date().toISOString().slice(0, 10);
    showMessage(form, '', '');
    dialog.showModal();

    return new Promise((resolve, reject) => {
      const onClose = () => {
        cleanup();
        reject(new ApiError('已取消上传', 0));
      };
      const onSubmit = async (event) => {
        event.preventDefault();
        const file = form.elements.file.files[0];
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
          showMessage(form, '请选择 PDF 文件');
          return;
        }
        if (file.size > 10 * 1024 * 1024) {
          showMessage(form, 'PDF 不能超过 10 MB');
          return;
        }
        const body = new FormData(form);
        body.set('current', form.elements.current.checked ? 'true' : 'false');
        body.set('privacyConfirmed', form.elements.privacyConfirmed.checked ? 'true' : 'false');
        const button = form.querySelector('[type="submit"]');
        button.disabled = true;
        showMessage(form, '正在上传并建立版本记录…', 'info');
        try {
          await request('/admin/resumes', { method: 'POST', headers: adminHeaders(), body });
          cleanup();
          dialog.close();
          window.dispatchEvent(new CustomEvent('resume-repository-changed'));
          resolve();
        } catch (error) {
          if (error.status === 401) setToken('');
          showMessage(form, error.message || '上传失败');
        } finally {
          button.disabled = false;
        }
      };
      const cleanup = () => {
        dialog.removeEventListener('close', onClose);
        form.removeEventListener('submit', onSubmit);
      };
      dialog.addEventListener('close', onClose, { once: true });
      form.addEventListener('submit', onSubmit);
    });
  }

  async function remove(resumeId) {
    await ensureAdmin();
    await request(`/admin/resumes/${encodeURIComponent(resumeId)}`, { method: 'DELETE', headers: adminHeaders() });
    window.dispatchEvent(new CustomEvent('resume-repository-changed'));
    return true;
  }

  async function setCurrent(resumeId) {
    await ensureAdmin();
    await request(`/admin/resumes/${encodeURIComponent(resumeId)}/current`, { method: 'PUT', headers: adminHeaders() });
    window.dispatchEvent(new CustomEvent('resume-repository-changed'));
  }

  function logout() {
    setToken('');
    window.dispatchEvent(new CustomEvent('resume-repository-changed'));
  }

  window.ResumeRepository = { ApiError, getToken, list, login: ensureAdmin, logout, openUpload, remove, setCurrent };
})();
