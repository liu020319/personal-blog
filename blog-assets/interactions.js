(function () {
  'use strict';

  const apiBase = String(window.BLOG_DATA?.resume?.api || './blog-api').replace(/\/$/, '');
  const agentApiBase = './agent-api';
  const visitorKey = 'xiaoliu-blog-visitor-id';

  class InteractionError extends Error {
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
    if (!response.ok) throw new InteractionError(payload.message || `请求失败（${response.status}）`, response.status);
    return payload;
  }

  function visitorId() {
    let value = localStorage.getItem(visitorKey);
    if (!value) {
      const random = globalThis.crypto?.randomUUID?.().replaceAll('-', '') || `${Date.now()}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`;
      value = `visitor_${random}`;
      localStorage.setItem(visitorKey, value);
    }
    return value;
  }

  function jsonOptions(payload, method = 'POST', admin = false) {
    const headers = { 'Content-Type': 'application/json' };
    if (admin) {
      const token = window.ResumeRepository?.getToken() || '';
      headers.Authorization = `Bearer ${token}`;
    }
    return { method, headers, body: JSON.stringify(payload) };
  }

  const interaction = (slug) => request(`/articles/${encodeURIComponent(slug)}/interaction`);
  const articles = () => request('/articles');
  const like = (slug) => request(`/articles/${encodeURIComponent(slug)}/likes`, jsonOptions({ visitorId: visitorId() }));
  const comment = (slug, payload) => request(`/articles/${encodeURIComponent(slug)}/comments`, jsonOptions(payload));
  const contact = (payload) => request('/contact', jsonOptions(payload));

  async function adminRequest(path, options = {}) {
    const token = window.ResumeRepository?.getToken() || '';
    if (!token) throw new InteractionError('请先进入管理模式', 401);
    try {
      return await request(path, { ...options, headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) } });
    } catch (error) {
      if (error.status === 401) window.ResumeRepository?.logout();
      throw error;
    }
  }

  const adminComments = (status = 'pending') => adminRequest(`/admin/comments?status=${encodeURIComponent(status)}`);
  const approveComment = (id) => adminRequest(`/admin/comments/${encodeURIComponent(id)}/approve`, { method: 'PUT' });
  const deleteComment = (id) => adminRequest(`/admin/comments/${encodeURIComponent(id)}`, { method: 'DELETE' });
  const adminLeads = (status = 'all') => adminRequest(`/admin/leads?status=${encodeURIComponent(status)}`);
  const setLeadStatus = (id, status) => adminRequest(`/admin/leads/${encodeURIComponent(id)}/status`, jsonOptions({ status }, 'PUT', true));
  const deleteLead = (id) => adminRequest(`/admin/leads/${encodeURIComponent(id)}`, { method: 'DELETE' });
  const createArticle = (payload) => adminRequest('/admin/articles', jsonOptions(payload, 'POST', true));
  const deleteArticle = (slug) => adminRequest(`/admin/articles/${encodeURIComponent(slug)}`, { method: 'DELETE' });
  const emailStatus = () => adminRequest('/admin/email-status');
  const testEmail = () => adminRequest('/admin/email/test', { method: 'POST' });

  async function agentMetrics() {
    const token = window.ResumeRepository?.getToken() || '';
    if (!token) throw new InteractionError('请先进入管理模式', 401);
    const response = await fetch(`${agentApiBase}/admin/metrics`, {
      cache: 'no-store',
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new InteractionError(payload.message || `Agent 状态读取失败（${response.status}）`, response.status);
    return payload;
  }

  window.BlogInteractions = {
    InteractionError,
    articles,
    interaction,
    like,
    comment,
    contact,
    adminComments,
    approveComment,
    deleteComment,
    adminLeads,
    setLeadStatus,
    deleteLead,
    createArticle,
    deleteArticle,
    emailStatus,
    testEmail,
    agentMetrics
  };
})();
