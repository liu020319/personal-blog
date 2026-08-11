(function () {
  'use strict';

  const data = window.BLOG_DATA;
  const main = document.getElementById('main-content');
  const rootUrl = window.location.href.split('#')[0];
  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const stripHtml = (value) => String(value).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const formatDate = (date) => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(`${date}T00:00:00`));
  const formatDateTime = (value) => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  const getTags = () => [...new Set(data.posts.flatMap((post) => post.tags))];
  const routeParts = () => (location.hash.slice(2).split('?')[0] || '').split('/').filter(Boolean).map(decodeURIComponent);

  function icon(name) {
    const icons = {
      arrow: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>',
      external: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M14 5h5v5M10 14 19 5M19 13v6H5V5h6"/></svg>',
      github: '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7.4A5.8 5.8 0 0 0 19.3 3 5.4 5.4 0 0 0 19.1-.9S17.9-1.3 15 1.1a13.4 13.4 0 0 0-7 0C5.1-1.3 3.9-.9 3.9-.9A5.4 5.4 0 0 0 3.7 3a5.8 5.8 0 0 0-1.5 4.1c0 5.8 3.5 7 6.8 7.4A4.8 4.8 0 0 0 8 18v4m0-3c-3 .9-3-1.5-4.2-2"/></svg>'
    };
    return icons[name] || '';
  }

  function postCard(post) {
    return `<article class="post-card">
      <div class="post-meta"><span>${escapeHtml(post.category)}</span><time datetime="${post.date}">${formatDate(post.date)}</time><span>${post.readingMinutes} 分钟</span></div>
      <h3><a href="#/article/${encodeURIComponent(post.slug)}">${escapeHtml(post.title)}</a></h3>
      <p>${escapeHtml(post.excerpt)}</p>
      <div class="post-card-bottom"><div class="tag-list">${post.tags.map((tag) => `<a href="#/articles?tag=${encodeURIComponent(tag)}">#${escapeHtml(tag)}</a>`).join('')}</div><a class="text-link" href="#/article/${encodeURIComponent(post.slug)}">阅读全文 ${icon('arrow')}</a></div>
    </article>`;
  }

  function projectCard(project, featured) {
    return `<article class="project-card ${featured ? 'project-featured' : ''} accent-${escapeHtml(project.accent)}">
      <div class="project-card-top"><span class="project-index">${project.name.slice(0, 1)}</span><span class="status-dot"><i></i>${escapeHtml(project.status)}</span></div>
      <div><p class="eyebrow">PROJECT · ${escapeHtml(project.id.toUpperCase())}</p><h3>${escapeHtml(project.name)}</h3><h4>${escapeHtml(project.subtitle)}</h4><p>${escapeHtml(project.description)}</p></div>
      <div class="stack-list">${project.stack.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}</div>
      <div class="project-actions"><a class="primary-button" href="${escapeHtml(project.url)}" target="_blank" rel="noreferrer">进入项目登录页 ${icon('external')}</a><a class="secondary-button" href="${escapeHtml(project.source)}" target="_blank" rel="noreferrer">查看源码 ${icon('github')}</a></div>
    </article>`;
  }

  function serviceCard(service, detailed = false) {
    return `<article class="service-card accent-${escapeHtml(service.accent)}">
      <div class="service-card-head"><span>${service.name.slice(0, 1)}</span><p class="eyebrow">${escapeHtml(service.audience)}</p></div>
      <h3>${escapeHtml(service.name)}</h3><p>${escapeHtml(service.description)}</p>
      <ul>${service.highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
      ${detailed ? `<a class="text-link" href="${escapeHtml(data.profile.github)}" target="_blank" rel="noreferrer">通过 GitHub 联系小刘 ${icon('external')}</a>` : `<a class="text-link" href="#/services">查看合作方式 ${icon('arrow')}</a>`}
    </article>`;
  }

  function renderHome() {
    const featured = data.projects.find((project) => project.featured) || data.projects[0];
    const latest = [...data.posts].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);
    main.innerHTML = `<section class="hero"><div class="shell hero-grid">
      <div class="hero-copy"><p class="eyebrow"><span></span> AVAILABLE FOR NEW OPPORTUNITIES</p><h1>把复杂系统<br>做得<span>清楚、可靠。</span></h1><p class="hero-intro">${escapeHtml(data.profile.intro)}</p><div class="hero-actions"><a class="primary-button" href="#/projects">查看我的项目 ${icon('arrow')}</a><a class="secondary-button" href="#/services">找我合作</a></div><div class="hero-notes"><span>Java / Spring Boot</span><span>Vue / MySQL</span><span>${escapeHtml(data.profile.location)}</span></div></div>
      <div class="hero-visual" aria-label="个人技术方向概览"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="code-window"><div class="window-head"><i></i><i></i><i></i><span>about.java</span></div><pre><code><b>public class</b> Developer {
  String focus = <em>"Backend"</em>;
  String principle = <em>"Reliable"</em>;

  <b>void</b> build() {
    understand();
    simplify();
    verify();
  }
}</code></pre></div><div class="floating-chip chip-one">SPRING BOOT</div><div class="floating-chip chip-two">VUE 3</div><div class="floating-chip chip-three">MYSQL</div></div>
    </div></section>
    <section class="section project-spotlight"><div class="shell"><div class="section-heading"><div><p class="eyebrow">FEATURED PROJECT</p><h2>项目不只展示截图，<br>也可以直接体验。</h2></div><p>每个项目拥有独立入口。点击卡片即可进入线上系统；以后新增项目，只需补充一项配置。</p></div>${projectCard(featured, true)}</div></section>
    <section class="section service-preview-section"><div class="shell"><div class="section-heading"><div><p class="eyebrow">WORK WITH ME</p><h2>有想法，可以一起<br>把它真正做出来。</h2></div><p>面向学生的项目陪跑与面向真实需求的开发兼职分别管理，先确认目标和边界，再进入开发与交付。</p></div><div class="service-grid">${data.services.map((service) => serviceCard(service)).join('')}</div></div></section>
    <section class="section latest-section"><div class="shell"><div class="section-heading compact"><div><p class="eyebrow">LATEST WRITING</p><h2>最近文章</h2></div><a class="text-link" href="#/articles">浏览全部文章 ${icon('arrow')}</a></div><div class="post-list">${latest.map(postCard).join('')}</div></div></section>
    <section class="section principles"><div class="shell principles-grid"><div><p class="eyebrow">HOW I WORK</p><h2>我的工作方式</h2></div><div class="principle-list"><article><span>01</span><div><h3>先理解业务，再设计代码</h3><p>把角色、状态和边界说清楚，避免用更多代码掩盖需求问题。</p></div></article><article><span>02</span><div><h3>用证据完成验证</h3><p>构建成功、服务运行、业务可用是三件事，每一步都保留清晰边界。</p></div></article><article><span>03</span><div><h3>让复杂度有明确价值</h3><p>选择满足当前规模的方案，同时为下一次扩展留下清楚入口。</p></div></article></div></div></section>`;
  }

  function renderArticles() {
    const params = new URLSearchParams((location.hash.split('?')[1] || ''));
    const activeTag = params.get('tag') || '';
    const posts = activeTag ? data.posts.filter((post) => post.tags.includes(activeTag)) : data.posts;
    main.innerHTML = `<section class="page-hero"><div class="shell"><p class="eyebrow">WRITING</p><h1>技术文章</h1><p>记录项目实践、问题排查和工程选择。每篇文章都尽量讲清问题、判断和验证边界。</p></div></section><section class="section page-section"><div class="shell articles-layout"><aside class="filter-panel"><h2>按标签浏览</h2><a class="filter-tag ${!activeTag ? 'active' : ''}" href="#/articles">全部文章 <span>${data.posts.length}</span></a>${getTags().map((tag) => `<a class="filter-tag ${activeTag === tag ? 'active' : ''}" href="#/articles?tag=${encodeURIComponent(tag)}">${escapeHtml(tag)} <span>${data.posts.filter((post) => post.tags.includes(tag)).length}</span></a>`).join('')}</aside><div><div class="result-heading"><span>${activeTag ? `标签：${escapeHtml(activeTag)}` : '全部文章'}</span><strong>${posts.length} 篇</strong></div><div class="post-list">${posts.length ? posts.map(postCard).join('') : '<div class="empty-state">这个标签下暂时没有文章。</div>'}</div></div></div></section>`;
  }

  function renderArchive() {
    const groups = data.posts.reduce((acc, post) => {
      const year = post.date.slice(0, 4);
      if (!acc[year]) acc[year] = [];
      acc[year].push(post);
      return acc;
    }, {});
    main.innerHTML = `<section class="page-hero"><div class="shell"><p class="eyebrow">ARCHIVE</p><h1>文章归档</h1><p>按时间回看学习、开发与复盘留下的轨迹。</p></div></section><section class="section page-section"><div class="shell archive">${Object.entries(groups).sort(([a], [b]) => b.localeCompare(a)).map(([year, posts]) => `<section class="archive-year"><h2>${year}</h2><div>${posts.sort((a, b) => b.date.localeCompare(a.date)).map((post) => `<a href="#/article/${encodeURIComponent(post.slug)}"><time>${post.date.slice(5).replace('-', '.')}</time><span>${escapeHtml(post.title)}</span><small>${escapeHtml(post.category)}</small></a>`).join('')}</div></section>`).join('')}</div></section>`;
  }

  function renderProjects() {
    main.innerHTML = `<section class="page-hero projects-hero"><div class="shell"><p class="eyebrow">PROJECT SPACE</p><h1>项目空间</h1><p>这里集中展示我独立完成或深入参与的项目。线上项目提供直接入口，后续作品会持续加入。</p></div></section><section class="section page-section"><div class="shell"><div class="project-grid">${data.projects.map((project) => projectCard(project, false)).join('')}<article class="project-card project-coming"><div class="coming-plus">+</div><p class="eyebrow">NEXT PROJECT</p><h3>下一个项目</h3><p>预留的扩展位置。新增项目只需在 <code>blog-assets/data.js</code> 中增加名称、简介、技术栈和登录地址。</p></article></div><div class="project-note"><strong>关于项目入口</strong><p>点击“进入项目登录页”会在新窗口打开独立业务系统。博客不保存业务账号、密码或生产配置。</p></div></div></section>`;
  }

  function renderServices() {
    main.innerHTML = `<section class="page-hero services-hero"><div class="shell"><p class="eyebrow">WORK WITH ME</p><h1>合作服务</h1><p>无论是第一次把想法做成完整项目，还是已有系统需要继续开发，都会先把目标、范围、时间和验收方式说清楚。</p></div></section>
    <section class="section services-main"><div class="shell"><div class="service-grid detailed">${data.services.map((service) => serviceCard(service, true)).join('')}</div></div></section>
    <section class="section service-process"><div class="shell"><div class="section-heading"><div><p class="eyebrow">DELIVERY PROCESS</p><h2>提前体验一次完整的<br>企业开发流程。</h2></div><p>不是只交付一份代码，而是让需求、开发、测试、发布和验证都有可以回看的过程。</p></div><ol class="process-grid"><li><span>01</span><h3>需求确认</h3><p>明确使用者、核心场景、已有材料、时间要求和最终交付物。</p></li><li><span>02</span><h3>方案与计划</h3><p>拆分功能、选择技术栈、确定里程碑，并提前说明不包含的范围。</p></li><li><span>03</span><h3>阶段开发</h3><p>使用分支、提交记录、代码讲解和阶段演示，让过程透明可跟进。</p></li><li><span>04</span><h3>测试与上线</h3><p>覆盖关键流程、异常场景、打包部署、回滚准备和线上验证。</p></li></ol></div></section>
    <section class="section cooperation-boundaries"><div class="shell boundary-grid"><article><p class="eyebrow">GRADUATION PROJECT</p><h2>毕设陪跑边界</h2><p>支持选题分析、项目定制、代码实现指导、问题排查、部署演示和答辩思路梳理；学生需要理解并参与自己的项目。</p><strong>不代写论文、不伪造实验数据、不冒名提交或替代答辩。</strong></article><article><p class="eyebrow">FREELANCE DEVELOPMENT</p><h2>兼职合作边界</h2><p>适合范围明确的功能开发、系统迭代、数据报表、故障排查和上线部署。涉及现有系统时，只接收完成任务所必需的最小资料。</p><strong>账号密码、生产数据和公司保密材料不得通过公开仓库传递。</strong></article></div></section>
    <section class="section service-contact"><div class="shell service-contact-layout"><div class="service-contact-copy"><p class="eyebrow">START A CONVERSATION</p><h2>把你的想法告诉我。</h2><p>填写的联系方式只会出现在小刘的管理中心，不会公开展示。请不要提交密码、生产数据或公司保密材料。</p><a class="text-link" href="${escapeHtml(data.profile.github)}" target="_blank" rel="noreferrer">也可以先查看小刘的 GitHub ${icon('external')}</a></div><form class="contact-form" id="contact-form"><div class="form-grid"><label class="field-label">怎么称呼你<input name="name" maxlength="30" required placeholder="例如：张同学" /></label><label class="field-label">联系方式类型<select name="contactMethod" required><option value="微信">微信</option><option value="电话">电话</option><option value="邮箱">邮箱</option><option value="其他">其他</option></select></label><label class="field-label field-wide">微信号、电话或邮箱<input name="contactValue" minlength="3" maxlength="100" required placeholder="仅管理员可见" /></label><label class="field-label field-wide">需求说明<textarea name="requirement" minlength="10" maxlength="1500" rows="6" required placeholder="想解决什么问题、谁来使用、希望什么时候完成、是否需要部署上线"></textarea></label><label class="form-trap" aria-hidden="true">网站<input name="website" tabindex="-1" autocomplete="off" /></label></div><label class="privacy-confirm"><input name="privacyConfirmed" type="checkbox" required /><span>我同意小刘仅为本次合作沟通保存和使用以上联系方式。</span></label><p class="form-message" aria-live="polite"></p><button class="primary-button" type="submit">提交合作需求</button></form></div></section>`;
    const contactForm = document.getElementById('contact-form');
    contactForm.dataset.startedAt = String(Date.now());
    contactForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = contactForm.querySelector('.form-message');
      const button = contactForm.querySelector('[type="submit"]');
      button.disabled = true; message.dataset.type = 'info'; message.textContent = '正在安全提交…';
      try {
        const form = new FormData(contactForm);
        const result = await window.BlogInteractions.contact({ name: form.get('name'), contactMethod: form.get('contactMethod'), contactValue: form.get('contactValue'), requirement: form.get('requirement'), privacyConfirmed: form.get('privacyConfirmed') === 'on', website: form.get('website'), startedAt: Number(contactForm.dataset.startedAt) });
        message.dataset.type = 'success'; message.textContent = result.message;
        contactForm.reset(); contactForm.dataset.startedAt = String(Date.now());
      } catch (error) {
        message.dataset.type = 'error'; message.textContent = error.message || '提交失败，请稍后重试。';
      } finally { button.disabled = false; }
    });
  }

  async function renderResume() {
    const repository = window.ResumeRepository;
    main.innerHTML = '<section class="section resume-loading"><div class="shell"><p>正在读取简历仓库…</p></div></section>';
    const result = repository ? await repository.list() : { online: false, items: data.resume.history || [] };
    if (routeParts()[0] !== 'resume') return;
    const items = [...result.items].sort((a, b) => Number(b.current) - Number(a.current) || b.date.localeCompare(a.date));
    const current = items.find((item) => item.current) || items[0];
    const isAdmin = Boolean(repository?.getToken());
    const timeline = items.length ? items.map((item) => `<article class="resume-version ${item.current ? 'current' : ''}">
      <div class="resume-version-marker"><i></i><span>${escapeHtml(item.date)}</span></div>
      <div class="resume-version-card"><div class="resume-version-head"><div><p class="eyebrow">${escapeHtml(item.version)}</p><h3>${escapeHtml(item.stage)}</h3></div>${item.current ? '<span class="current-badge">当前版本</span>' : ''}</div><p>${escapeHtml(item.change)}</p><div class="resume-version-actions"><a class="text-link" href="${escapeHtml(item.file)}" target="_blank" rel="noreferrer">在线查看 ${icon('external')}</a><a class="text-link muted-link" href="${escapeHtml(item.file)}" download>下载存档</a>${item.current ? '' : `<button class="text-button set-current-resume" type="button" data-resume-id="${escapeHtml(item.id)}">设为当前版</button>`}<button class="text-button danger-text delete-resume" type="button" data-resume-id="${escapeHtml(item.id)}" data-resume-label="${escapeHtml(item.version)}">删除</button></div></div>
    </article>`).join('') : '<div class="resume-empty"><span>0</span><h3>简历仓库还是空的</h3><p>点击“上传新简历”，从刚毕业的版本开始建立你的成长时间线。</p></div>';

    const currentBlock = current ? `<div class="resume-showcase"><div class="resume-showcase-copy"><span class="resume-version-label">${escapeHtml(current.version)}</span><h3>${escapeHtml(current.stage)}</h3><p>更新于 ${formatDate(current.date)}。这份文件由小刘主动上传并设为当前公开版本。</p><div class="resume-actions"><a class="primary-button" href="${escapeHtml(current.file)}" target="_blank" rel="noreferrer">在线查看 PDF ${icon('external')}</a><a class="secondary-button" href="${escapeHtml(current.file)}" download>下载简历</a></div><div class="resume-safety"><strong>公开边界</strong><span>上传前必须完成隐私和保密检查；管理口令不会写入网页或 GitHub。</span></div></div><div class="resume-preview"><object data="${escapeHtml(current.file)}#toolbar=0&navpanes=0" type="application/pdf" aria-label="小刘当前公开简历预览"><div class="pdf-fallback"><p>当前浏览器不支持内嵌 PDF。</p><a class="primary-button" href="${escapeHtml(current.file)}" target="_blank" rel="noreferrer">打开简历</a></div></object></div></div>` : '<div class="resume-current-empty"><span>PDF</span><h3>还没有当前公开简历</h3><p>进入管理模式后上传 PDF，可以将任意历史版本设为当前版。</p></div>';

    main.innerHTML = `<section class="page-hero resume-hero"><div class="shell resume-hero-grid"><div><p class="eyebrow">RESUME REPOSITORY</p><h1>简历仓库</h1><p>简历不只是一张求职页面，也是一份阶段记录。这里保存当前公开简历和历史版本，持续观察能力、项目与职业定位如何变化。</p></div><div class="resume-admin-actions"><button class="primary-button" id="upload-resume" type="button">上传新简历</button><button class="secondary-button" id="resume-login" type="button">${isAdmin ? '退出管理' : '进入管理'}</button></div></div></section>
    ${result.online ? '' : '<section class="service-notice"><div class="shell"><strong>简历服务尚未连接</strong><span>静态页面已经就绪，完成服务器端简历服务部署后即可上传和删除。</span></div></section>'}
    <section class="section resume-current"><div class="shell"><div class="section-heading"><div><p class="eyebrow">CURRENT RESUME</p><h2>当前公开简历</h2></div><p>公开区不预置示例文件，只展示你亲自上传并确认可以公开的真实历史版本。</p></div>${currentBlock}</div></section>
    <section class="section resume-history"><div class="shell resume-history-grid"><div class="resume-history-heading"><p class="eyebrow">VERSION HISTORY</p><h2>成长时间线</h2><p>每份文件独立保存。你可以上传、设为当前版或删除，旧版本不会被新文件覆盖。</p></div><div class="resume-timeline">${timeline}</div></div></section>
    <section class="section resume-method"><div class="shell resume-method-grid"><div><p class="eyebrow">HOW IT WORKS</p><h2>上传前的三道检查</h2></div><ol><li><span>01</span><div><strong>保留原文件</strong><p>本地原始简历不做任何修改，博客保存单独的公开副本。</p></div></li><li><span>02</span><div><strong>完成脱敏</strong><p>删除真实姓名、私人联系方式、地址、账号密码以及不应公开的公司项目细节。</p></div></li><li><span>03</span><div><strong>记录阶段变化</strong><p>写清这版简历的定位、项目表达和能力重点发生了什么变化。</p></div></li></ol></div></section>`;

    const handleError = (error) => { if (error?.status !== 0) window.alert(error?.message || '操作失败，请稍后重试。'); };
    document.getElementById('upload-resume')?.addEventListener('click', () => repository?.openUpload().catch(handleError));
    document.getElementById('resume-login')?.addEventListener('click', () => {
      if (!repository) return;
      if (repository.getToken()) repository.logout();
      else repository.login().then(renderResume).catch(handleError);
    });
    document.querySelectorAll('.delete-resume').forEach((button) => button.addEventListener('click', () => repository?.remove(button.dataset.resumeId, button.dataset.resumeLabel).catch(handleError)));
    document.querySelectorAll('.set-current-resume').forEach((button) => button.addEventListener('click', () => repository?.setCurrent(button.dataset.resumeId).catch(handleError)));
  }

  function renderAbout() {
    main.innerHTML = `<section class="page-hero about-hero"><div class="shell about-intro"><div><p class="eyebrow">ABOUT ME</p><h1>你好，我是${escapeHtml(data.profile.name)}。</h1><p>${escapeHtml(data.profile.intro)}</p><div class="about-actions"><a class="primary-button" href="${escapeHtml(data.profile.github)}" target="_blank" rel="noreferrer">访问 GitHub ${icon('external')}</a><a class="secondary-button" href="#/resume">查看简历</a></div></div><div class="portrait-card"><span>XL</span><p>${escapeHtml(data.profile.role)}</p><small>${escapeHtml(data.profile.location)}</small></div></div></section><section class="section page-section"><div class="shell about-grid"><div><p class="eyebrow">FOCUS</p><h2>我关注的方向</h2></div><div class="about-content"><p class="large-copy">以 Java 后端为主线，同时具备 Vue 前端落地能力。我更关心系统是否真正解决业务问题，以及数据在整个流程中是否准确、可追溯。</p><div class="skill-grid"><article><span>01</span><h3>后端开发</h3><p>Spring Boot、REST API、权限、事务、业务状态和异常处理。</p></article><article><span>02</span><h3>数据与分析</h3><p>MySQL、SQL 查询、数据口径、报表和问题定位。</p></article><article><span>03</span><h3>前端交付</h3><p>Vue 3、响应式界面、后台工作台和业务交互。</p></article><article><span>04</span><h3>部署与验证</h3><p>Nginx、Linux、备份、发布检查和故障排查。</p></article></div></div></div></section>`;
  }

  async function renderManage() {
    const repository = window.ResumeRepository;
    const interactions = window.BlogInteractions;
    main.innerHTML = '<section class="section manage-loading"><div class="shell"><p>正在读取站点管理数据…</p></div></section>';
    if (!repository?.getToken()) {
      main.innerHTML = `<section class="page-hero"><div class="shell"><p class="eyebrow">SITE ADMIN</p><h1>站点管理</h1><p>合作联系方式、待审核评论和简历管理都使用同一份服务器管理口令。</p></div></section><section class="section"><div class="shell manage-login-card"><span>LOCKED</span><h2>请输入管理口令</h2><p>口令只保存在当前浏览器会话，关闭页面后自动清除。</p><button class="primary-button" id="manage-login" type="button">进入管理中心</button></div></section>`;
      document.getElementById('manage-login').addEventListener('click', () => repository.login().then(renderManage).catch((error) => { if (error.status !== 0) window.alert(error.message); }));
      return;
    }
    try {
      const [commentResult, leadResult] = await Promise.all([interactions.adminComments('all'), interactions.adminLeads('all')]);
      if (routeParts()[0] !== 'manage') return;
      const comments = commentResult.items || [];
      const leads = leadResult.items || [];
      const postName = (slug) => data.posts.find((post) => post.slug === slug)?.title || slug;
      const commentCards = comments.length ? comments.map((comment) => `<article class="manage-item"><div class="manage-item-head"><div><span class="status-pill status-${escapeHtml(comment.status)}">${comment.status === 'pending' ? '待审核' : '已公开'}</span><h3>${escapeHtml(comment.nickname)} · ${escapeHtml(postName(comment.article_slug))}</h3></div><time>${formatDateTime(comment.created_at)}</time></div><p>${escapeHtml(comment.content)}</p><div class="manage-actions">${comment.status === 'pending' ? `<button class="primary-button approve-comment" data-id="${escapeHtml(comment.id)}" type="button">批准公开</button>` : `<a class="secondary-button" href="#/article/${encodeURIComponent(comment.article_slug)}">查看文章</a>`}<button class="secondary-button delete-comment" data-id="${escapeHtml(comment.id)}" type="button">删除评论</button></div></article>`).join('') : '<div class="manage-empty">目前没有评论记录。</div>';
      const leadCards = leads.length ? leads.map((lead) => `<article class="manage-item lead-item"><div class="manage-item-head"><div><span class="status-pill status-${escapeHtml(lead.status)}">${({ new: '新留言', contacted: '已联系', closed: '已结束' })[lead.status]}</span><h3>${escapeHtml(lead.name)} · ${escapeHtml(lead.contact_method)}</h3></div><time>${formatDateTime(lead.created_at)}</time></div><button class="contact-value copy-contact" type="button" data-value="${escapeHtml(lead.contact_value)}" title="点击复制">${escapeHtml(lead.contact_value)} <small>复制</small></button><p>${escapeHtml(lead.requirement)}</p><div class="manage-actions"><select class="lead-status" data-id="${escapeHtml(lead.id)}" aria-label="更新合作状态"><option value="new" ${lead.status === 'new' ? 'selected' : ''}>新留言</option><option value="contacted" ${lead.status === 'contacted' ? 'selected' : ''}>已联系</option><option value="closed" ${lead.status === 'closed' ? 'selected' : ''}>已结束</option></select><button class="secondary-button delete-lead" data-id="${escapeHtml(lead.id)}" type="button">删除记录</button></div></article>`).join('') : '<div class="manage-empty">目前没有合作留言。</div>';
      main.innerHTML = `<section class="page-hero manage-hero"><div class="shell manage-hero-grid"><div><p class="eyebrow">SITE ADMIN</p><h1>站点管理</h1><p>联系方式不会公开显示；评论只有批准后才会出现在文章下方。</p></div><button class="secondary-button" id="manage-logout" type="button">退出管理</button></div></section><section class="section manage-summary"><div class="shell summary-grid"><article><span>${leads.filter((lead) => lead.status === 'new').length}</span><p>条新合作留言</p></article><article><span>${comments.filter((comment) => comment.status === 'pending').length}</span><p>条待审核评论</p></article><article><span>${comments.filter((comment) => comment.status === 'approved').length}</span><p>条已公开评论</p></article></div></section><section class="section manage-content"><div class="shell manage-columns"><section><div class="manage-section-heading"><p class="eyebrow">COOPERATION LEADS</p><h2>合作联系方式</h2></div><div class="manage-list">${leadCards}</div></section><section><div class="manage-section-heading"><p class="eyebrow">COMMENTS</p><h2>文章评论</h2></div><div class="manage-list">${commentCards}</div></section></div></section>`;
      const refresh = () => renderManage();
      document.getElementById('manage-logout').addEventListener('click', () => { repository.logout(); renderManage(); });
      document.querySelectorAll('.approve-comment').forEach((button) => button.addEventListener('click', () => interactions.approveComment(button.dataset.id).then(refresh).catch((error) => window.alert(error.message))));
      document.querySelectorAll('.delete-comment').forEach((button) => button.addEventListener('click', () => { if (window.confirm('确定删除这条评论吗？')) interactions.deleteComment(button.dataset.id).then(refresh).catch((error) => window.alert(error.message)); }));
      document.querySelectorAll('.lead-status').forEach((select) => select.addEventListener('change', () => interactions.setLeadStatus(select.dataset.id, select.value).then(refresh).catch((error) => window.alert(error.message))));
      document.querySelectorAll('.delete-lead').forEach((button) => button.addEventListener('click', () => { if (window.confirm('确定删除这条合作联系方式吗？删除后无法从网页恢复。')) interactions.deleteLead(button.dataset.id).then(refresh).catch((error) => window.alert(error.message)); }));
      document.querySelectorAll('.copy-contact').forEach((button) => button.addEventListener('click', async () => { await navigator.clipboard.writeText(button.dataset.value); button.querySelector('small').textContent = '已复制'; }));
    } catch (error) {
      if (error.status === 401) return renderManage();
      main.innerHTML = `<section class="section manage-loading"><div class="shell"><p>管理数据读取失败：${escapeHtml(error.message || '请检查服务状态')}</p></div></section>`;
    }
  }

  function renderArticle(slug) {
    const post = data.posts.find((item) => item.slug === slug);
    if (!post) return renderNotFound();
    const headings = [...post.content.matchAll(/<h2 id="([^"]+)">([^<]+)<\/h2>/g)];
    document.title = `${post.title} · 小刘`;
    main.innerHTML = `<article class="article"><header class="article-header"><div class="shell article-shell"><a class="back-link" href="#/articles">← 返回文章列表</a><div class="post-meta"><span>${escapeHtml(post.category)}</span><time datetime="${post.date}">${formatDate(post.date)}</time><span>${post.readingMinutes} 分钟阅读</span></div><h1>${escapeHtml(post.title)}</h1><p>${escapeHtml(post.excerpt)}</p><div class="tag-list large">${post.tags.map((tag) => `<a href="#/articles?tag=${encodeURIComponent(tag)}">#${escapeHtml(tag)}</a>`).join('')}</div></div></header><div class="shell article-layout"><aside class="toc"><strong>本文目录</strong>${headings.map((heading) => `<a href="#${escapeHtml(heading[1])}">${escapeHtml(heading[2])}</a>`).join('')}</aside><div class="article-body">${post.content}<div class="article-end"><span>END</span><p>如果这篇文章对你有帮助，欢迎继续浏览我的项目和其他记录。</p><div><a class="primary-button" href="#/projects">查看项目</a><button class="secondary-button share-button" type="button">复制文章链接</button></div></div></div></div><section class="article-community"><div class="shell community-layout"><aside class="like-panel"><p class="eyebrow">LIKE THIS POST</p><h2>这篇文章对你有帮助吗？</h2><button class="like-button" id="like-button" type="button"><span>♡</span><strong id="like-count">0</strong><small>点赞</small></button><p>每个浏览器对同一篇文章记录一次点赞，不保存你的 IP。</p></aside><div class="comment-panel"><div class="comment-heading"><div><p class="eyebrow">COMMENTS</p><h2>评论交流</h2></div><span id="comment-count">0 条公开评论</span></div><div class="comment-list" id="comment-list"><p class="comment-loading">正在读取评论…</p></div><form class="comment-form" id="comment-form"><h3>写下你的想法</h3><p>评论审核通过后公开显示。请勿填写电话、微信、邮箱或外部链接。</p><label class="field-label">怎么称呼你<input name="nickname" maxlength="30" required placeholder="例如：一名 Java 学习者" /></label><label class="field-label">评论内容<textarea name="content" minlength="4" maxlength="800" rows="5" required placeholder="说说你的看法或问题"></textarea></label><label class="form-trap" aria-hidden="true">网站<input name="website" tabindex="-1" autocomplete="off" /></label><p class="form-message" aria-live="polite"></p><button class="primary-button" type="submit">提交评论</button></form></div></div></section></article>`;
    enhanceArticle(post);
  }

  function renderNotFound() {
    document.title = '页面未找到 · 小刘';
    main.innerHTML = `<section class="not-found"><div class="shell"><span>404</span><h1>这页暂时不存在</h1><p>可能是地址发生了变化，或者内容还没有发布。</p><a class="primary-button" href="#/">返回首页</a></div></section>`;
  }

  function enhanceArticle(post) {
    document.querySelectorAll('.article-body pre').forEach((block) => {
      const button = document.createElement('button');
      button.className = 'copy-button'; button.type = 'button'; button.textContent = '复制';
      button.addEventListener('click', async () => { await navigator.clipboard.writeText(block.innerText); button.textContent = '已复制'; setTimeout(() => { button.textContent = '复制'; }, 1500); });
      block.appendChild(button);
    });
    const shareButton = document.querySelector('.share-button');
    shareButton?.addEventListener('click', async () => { await navigator.clipboard.writeText(window.location.href); shareButton.textContent = '链接已复制'; setTimeout(() => { shareButton.textContent = '复制文章链接'; }, 1500); });
    const interactions = window.BlogInteractions;
    const likeButton = document.getElementById('like-button');
    const likeCount = document.getElementById('like-count');
    const commentList = document.getElementById('comment-list');
    const commentCount = document.getElementById('comment-count');
    const commentForm = document.getElementById('comment-form');
    const likedKey = `xiaoliu-liked-${post.slug}`;
    const renderComments = (comments) => {
      commentCount.textContent = `${comments.length} 条公开评论`;
      commentList.innerHTML = comments.length ? comments.map((comment) => `<article class="comment-item"><div><strong>${escapeHtml(comment.nickname)}</strong><time>${formatDateTime(comment.createdAt)}</time></div><p>${escapeHtml(comment.content)}</p></article>`).join('') : '<div class="comment-empty">还没有公开评论，欢迎留下第一条交流。</div>';
    };
    interactions.interaction(post.slug).then((result) => { likeCount.textContent = result.likeCount; renderComments(result.comments); }).catch(() => { commentList.innerHTML = '<div class="comment-empty">互动服务暂时不可用，文章仍可正常阅读。</div>'; });
    if (localStorage.getItem(likedKey)) { likeButton.classList.add('liked'); likeButton.querySelector('span').textContent = '♥'; }
    likeButton.addEventListener('click', async () => {
      likeButton.disabled = true;
      try { const result = await interactions.like(post.slug); likeCount.textContent = result.likeCount; likeButton.classList.add('liked'); likeButton.querySelector('span').textContent = '♥'; localStorage.setItem(likedKey, '1'); }
      catch (error) { window.alert(error.message || '点赞失败，请稍后重试。'); }
      finally { likeButton.disabled = false; }
    });
    commentForm.dataset.startedAt = String(Date.now());
    commentForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = commentForm.querySelector('.form-message');
      const button = commentForm.querySelector('[type="submit"]');
      const form = new FormData(commentForm);
      button.disabled = true; message.dataset.type = 'info'; message.textContent = '正在提交审核…';
      try {
        const result = await interactions.comment(post.slug, { nickname: form.get('nickname'), content: form.get('content'), website: form.get('website'), startedAt: Number(commentForm.dataset.startedAt) });
        message.dataset.type = 'success'; message.textContent = result.message; commentForm.reset(); commentForm.dataset.startedAt = String(Date.now());
      } catch (error) { message.dataset.type = 'error'; message.textContent = error.message || '提交失败，请稍后重试。'; }
      finally { button.disabled = false; }
    });
  }

  function route() {
    window.scrollTo(0, 0);
    document.title = '小刘 · 个人技术博客';
    document.body.classList.toggle('is-article', routeParts()[0] === 'article');
    const [section, detail] = routeParts();
    if (!section) renderHome();
    else if (section === 'articles') renderArticles();
    else if (section === 'article') renderArticle(detail);
    else if (section === 'archive') renderArchive();
    else if (section === 'projects') renderProjects();
    else if (section === 'services') renderServices();
    else if (section === 'resume') renderResume();
    else if (section === 'manage') renderManage();
    else if (section === 'about') renderAbout();
    else renderNotFound();
    updateActiveNav(section || 'home');
    closeMobileMenu();
  }

  function updateActiveNav(section) {
    document.querySelectorAll('.desktop-nav a, .mobile-nav a').forEach((link) => {
      const target = link.getAttribute('href').replace('#/', '').split('?')[0] || 'home';
      link.classList.toggle('active', target === section || (section === 'article' && target === 'articles'));
    });
  }

  const menuButton = document.getElementById('menu-button');
  const mobileNav = document.getElementById('mobile-nav');
  function closeMobileMenu() { mobileNav.hidden = true; menuButton.setAttribute('aria-expanded', 'false'); }
  menuButton.addEventListener('click', () => { const open = mobileNav.hidden; mobileNav.hidden = !open; menuButton.setAttribute('aria-expanded', String(open)); });

  const searchDialog = document.getElementById('search-dialog');
  const searchInput = document.getElementById('search-input');
  const searchResults = document.getElementById('search-results');
  function search(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) { searchResults.innerHTML = '<div class="search-empty">输入关键词，搜索文章标题、正文和标签。</div>'; return; }
    const results = data.posts.filter((post) => [post.title, post.excerpt, post.category, post.tags.join(' '), stripHtml(post.content)].join(' ').toLowerCase().includes(normalized));
    searchResults.innerHTML = results.length ? results.map((post) => `<a href="#/article/${encodeURIComponent(post.slug)}" class="search-result"><span>${escapeHtml(post.category)}</span><strong>${escapeHtml(post.title)}</strong><small>${escapeHtml(post.excerpt)}</small></a>`).join('') : `<div class="search-empty">没有找到“${escapeHtml(query)}”，换个关键词试试。</div>`;
  }
  function openSearch() { searchDialog.showModal(); searchInput.value = ''; search(''); setTimeout(() => searchInput.focus(), 50); }
  document.getElementById('search-button').addEventListener('click', openSearch);
  searchInput.addEventListener('input', (event) => search(event.target.value));
  searchResults.addEventListener('click', (event) => { if (event.target.closest('a')) searchDialog.close(); });
  searchDialog.addEventListener('click', (event) => { if (event.target === searchDialog) searchDialog.close(); });
  document.addEventListener('keydown', (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); openSearch(); } });

  const themeButton = document.getElementById('theme-button');
  const applyTheme = (theme) => { document.documentElement.dataset.theme = theme; localStorage.setItem('blog-theme', theme); document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#101816' : '#f7f4ed'; };
  const savedTheme = localStorage.getItem('blog-theme');
  applyTheme(savedTheme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  themeButton.addEventListener('click', () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));

  const backToTop = document.getElementById('back-to-top');
  const progress = document.getElementById('reading-progress');
  window.addEventListener('scroll', () => {
    backToTop.classList.toggle('visible', window.scrollY > 520);
    const height = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${height > 0 ? Math.min(100, (window.scrollY / height) * 100) : 0}%`;
  }, { passive: true });
  backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  document.getElementById('current-year').textContent = new Date().getFullYear();
  window.addEventListener('resume-repository-changed', () => { if (routeParts()[0] === 'resume') renderResume(); });
  window.addEventListener('hashchange', route);
  if (!location.hash) history.replaceState(null, '', `${rootUrl}#/`);
  route();
})();
