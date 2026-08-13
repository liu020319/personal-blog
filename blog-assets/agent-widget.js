(function () {
  'use strict';

  const API_BASE = './agent-api';
  const MAX_HISTORY = 8;
  const COOPERATION_DRAFT_KEY = 'xiaoliu-agent-cooperation-draft';
  const state = { busy: false, history: [] };

  const launcher = document.createElement('button');
  launcher.className = 'agent-launcher';
  launcher.type = 'button';
  launcher.setAttribute('aria-label', '打开小刘技术与项目助理');
  launcher.innerHTML = '<span class="agent-launcher-mark" aria-hidden="true">XL</span><span class="agent-launcher-copy">技术与项目助理</span>';

  const dialog = document.createElement('dialog');
  dialog.className = 'agent-dialog';
  dialog.setAttribute('aria-label', '小刘技术与项目助理');
  dialog.innerHTML = `
    <section class="agent-panel">
      <header class="agent-head">
        <span class="agent-head-mark" aria-hidden="true">XL</span>
        <div class="agent-head-copy"><strong>小刘技术与项目助理</strong><small>了解公开文章、康联云与合作服务</small></div>
        <button class="agent-close" type="button" aria-label="关闭技术助理">×</button>
      </header>
      <div class="agent-conversation" aria-live="polite">
        <div class="agent-intro">你好，我可以帮你查找小刘公开发布的技术文章，介绍康联云项目，也可以说明毕业设计陪跑和开发合作范围。涉及私人资料、服务器配置或保密内容的问题不会回答。</div>
      </div>
      <form class="agent-composer">
        <div class="agent-suggestions" aria-label="常用问题">
          <button class="agent-suggestion" type="button">康联云是做什么的？</button>
          <button class="agent-suggestion" type="button">毕设项目怎么合作？</button>
          <button class="agent-suggestion" type="button">推荐一篇后端排障文章</button>
        </div>
        <div class="agent-input-row">
          <input class="agent-input" type="text" maxlength="600" autocomplete="off" placeholder="问文章、项目或合作服务…" aria-label="输入问题" />
          <button class="agent-send" type="submit">发送</button>
        </div>
        <p class="agent-note">回答来自博客公开资料，由通义千问生成；具体合作以小刘确认结果为准。</p>
      </form>
    </section>`;

  document.body.append(launcher, dialog);

  const closeButton = dialog.querySelector('.agent-close');
  const conversation = dialog.querySelector('.agent-conversation');
  const form = dialog.querySelector('.agent-composer');
  const input = dialog.querySelector('.agent-input');
  const sendButton = dialog.querySelector('.agent-send');

  function setBusy(busy) {
    state.busy = busy;
    input.disabled = busy;
    sendButton.disabled = busy;
    sendButton.textContent = busy ? '回答中…' : '发送';
  }

  function scrollToLatest() {
    conversation.scrollTop = conversation.scrollHeight;
  }

  function safePublicUrl(value) {
    try {
      const url = new URL(value, window.location.origin);
      if (url.protocol !== 'https:' || !['xiaoliudev.com', 'github.com'].includes(url.hostname)) return null;
      return url.href;
    } catch (_) {
      return null;
    }
  }

  function openCooperationForm(handoff) {
    const visitorMessages = state.history
      .filter((item) => item.role === 'user')
      .slice(-5)
      .map((item) => `- ${item.content}`)
      .join('\n');
    const requirement = visitorMessages || String(handoff.draft || '').trim();
    try {
      sessionStorage.setItem(COOPERATION_DRAFT_KEY, JSON.stringify({
        source: 'agent',
        projectType: handoff.projectType || '其他技术需求',
        requirement: `我通过“小刘技术与项目助理”咨询了以下内容：\n${requirement}`.slice(0, 1100),
        createdAt: Date.now()
      }));
    } catch (_) {
      // 浏览器禁用会话存储时仍然允许进入合作页面。
    }
    dialog.close();
    const target = '#/services?source=agent';
    if (window.location.hash === target) window.dispatchEvent(new HashChangeEvent('hashchange'));
    else window.location.hash = target;
    window.setTimeout(() => document.getElementById('contact-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 120);
  }

  function addMessage(role, content, options = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = `agent-message ${role}${options.error ? ' error' : ''}${options.loading ? ' loading' : ''}`;
    const card = document.createElement('div');
    card.className = 'agent-message-card';
    const text = document.createElement('div');
    text.textContent = content;
    card.appendChild(text);

    if (Array.isArray(options.sources) && options.sources.length) {
      const sources = document.createElement('div');
      sources.className = 'agent-sources';
      options.sources.forEach((source) => {
        const href = safePublicUrl(source.url);
        if (!href) return;
        const link = document.createElement('a');
        link.className = 'agent-source';
        link.href = href;
        link.textContent = source.title || '查看资料';
        link.target = href.includes('github.com') ? '_blank' : '_self';
        link.rel = 'noreferrer';
        sources.appendChild(link);
      });
      card.appendChild(sources);
    }

    if (options.handoff) {
      const href = safePublicUrl(options.handoff.url);
      if (href) {
        const link = document.createElement('a');
        link.className = 'agent-handoff';
        link.href = href;
        link.textContent = options.handoff.label || '填写合作需求';
        link.addEventListener('click', (event) => {
          event.preventDefault();
          openCooperationForm(options.handoff);
        });
        card.appendChild(link);
      }
    }

    wrapper.appendChild(card);
    conversation.appendChild(wrapper);
    scrollToLatest();
    return wrapper;
  }

  async function ask(rawMessage) {
    const message = String(rawMessage || '').trim();
    if (state.busy || message.length < 2) return;
    const requestHistory = state.history.slice(-MAX_HISTORY);
    addMessage('user', message);
    state.history.push({ role: 'user', content: message });
    input.value = '';
    setBusy(true);
    const loading = addMessage('assistant', '正在查找公开资料…', { loading: true });

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        cache: 'no-store',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history: requestHistory })
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.message || `请求失败（${response.status}）`);
      loading.remove();
      addMessage('assistant', payload.answer, { sources: payload.sources, handoff: payload.handoff });
      state.history.push({ role: 'assistant', content: payload.answer });
      state.history = state.history.slice(-MAX_HISTORY);
    } catch (error) {
      loading.remove();
      addMessage('assistant', error.message || '技术助理暂时不可用，请稍后再试。', { error: true });
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  launcher.addEventListener('click', () => {
    dialog.showModal();
    window.setTimeout(() => input.focus(), 0);
  });
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    ask(input.value);
  });
  dialog.querySelectorAll('.agent-suggestion').forEach((button) => {
    button.addEventListener('click', () => ask(button.textContent));
  });
})();
