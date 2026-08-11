(function () {
  'use strict';

  const data = window.BLOG_DATA;
  const main = document.getElementById('main-content');
  const rootUrl = window.location.href.split('#')[0];
  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const stripHtml = (value) => String(value).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  const formatDate = (date) => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(`${date}T00:00:00`));
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

  function renderHome() {
    const featured = data.projects.find((project) => project.featured) || data.projects[0];
    const latest = [...data.posts].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);
    main.innerHTML = `<section class="hero"><div class="shell hero-grid">
      <div class="hero-copy"><p class="eyebrow"><span></span> AVAILABLE FOR NEW OPPORTUNITIES</p><h1>把复杂系统<br>做得<span>清楚、可靠。</span></h1><p class="hero-intro">${escapeHtml(data.profile.intro)}</p><div class="hero-actions"><a class="primary-button" href="#/projects">查看我的项目 ${icon('arrow')}</a><a class="secondary-button" href="#/articles">阅读技术文章</a></div><div class="hero-notes"><span>Java / Spring Boot</span><span>Vue / MySQL</span><span>${escapeHtml(data.profile.location)}</span></div></div>
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

  function renderResume() {
    const current = data.resume.current;
    const timeline = data.resume.history.map((item) => `<article class="resume-version ${item.current ? 'current' : ''}">
      <div class="resume-version-marker"><i></i><span>${escapeHtml(item.date)}</span></div>
      <div class="resume-version-card"><div class="resume-version-head"><div><p class="eyebrow">${escapeHtml(item.version)}</p><h3>${escapeHtml(item.stage)}</h3></div>${item.current ? '<span class="current-badge">当前版本</span>' : ''}</div><p>${escapeHtml(item.change)}</p>${item.available ? `<div class="resume-version-actions"><a class="text-link" href="${escapeHtml(item.file)}" target="_blank" rel="noreferrer">在线查看 ${icon('external')}</a><a class="text-link muted-link" href="${escapeHtml(item.file)}" download>下载存档</a></div>` : '<span class="pending-label">等待补充历史文件</span>'}</div>
    </article>`).join('');

    main.innerHTML = `<section class="page-hero resume-hero"><div class="shell"><p class="eyebrow">RESUME REPOSITORY</p><h1>简历仓库</h1><p>简历不只是一张求职页面，也是一份阶段记录。这里保存当前公开简历和历史版本，持续观察能力、项目与职业定位如何变化。</p></div></section>
    <section class="section resume-current"><div class="shell"><div class="section-heading"><div><p class="eyebrow">CURRENT RESUME</p><h2>当前公开简历</h2></div><p>${escapeHtml(current.summary)}</p></div><div class="resume-showcase"><div class="resume-showcase-copy"><span class="resume-version-label">${escapeHtml(current.version)}</span><h3>${escapeHtml(current.title)}</h3><p>更新于 ${formatDate(current.updated)}。公开版本统一使用“小刘”，联系方式通过 GitHub，已移除私人电话、邮箱和项目演示账号。</p><div class="resume-actions"><a class="primary-button" href="${escapeHtml(current.file)}" target="_blank" rel="noreferrer">在线查看 PDF ${icon('external')}</a><a class="secondary-button" href="${escapeHtml(current.file)}" download>下载简历</a></div><div class="resume-safety"><strong>公开边界</strong><span>原始简历保留在本地；博客只展示经过隐私处理的副本。</span></div></div><div class="resume-preview"><object data="${escapeHtml(current.file)}#toolbar=0&navpanes=0" type="application/pdf" aria-label="小刘当前公开简历预览"><div class="pdf-fallback"><p>当前浏览器不支持内嵌 PDF。</p><a class="primary-button" href="${escapeHtml(current.file)}" target="_blank" rel="noreferrer">打开简历</a></div></object></div></div></div></section>
    <section class="section resume-history"><div class="shell resume-history-grid"><div class="resume-history-heading"><p class="eyebrow">VERSION HISTORY</p><h2>成长时间线</h2><p>旧版本不会覆盖。每次更新记录“为什么改”和“重点变了什么”，让成长过程真正可回看。</p></div><div class="resume-timeline">${timeline}</div></div></section>
    <section class="section resume-method"><div class="shell resume-method-grid"><div><p class="eyebrow">HOW IT WORKS</p><h2>如何加入下一版</h2></div><ol><li><span>01</span><div><strong>保留原文件</strong><p>新 PDF 使用日期或阶段命名，永远不覆盖旧版。</p></div></li><li><span>02</span><div><strong>生成公开副本</strong><p>统一使用“小刘”，发布前检查电话、邮箱、账号和文档元数据。</p></div></li><li><span>03</span><div><strong>记录阶段变化</strong><p>在版本配置中写明定位、项目和能力重点的变化。</p></div></li></ol></div></section>`;
  }

  function renderAbout() {
    main.innerHTML = `<section class="page-hero about-hero"><div class="shell about-intro"><div><p class="eyebrow">ABOUT ME</p><h1>你好，我是${escapeHtml(data.profile.name)}。</h1><p>${escapeHtml(data.profile.intro)}</p><div class="about-actions"><a class="primary-button" href="${escapeHtml(data.profile.github)}" target="_blank" rel="noreferrer">访问 GitHub ${icon('external')}</a><a class="secondary-button" href="#/resume">查看简历</a></div></div><div class="portrait-card"><span>XL</span><p>${escapeHtml(data.profile.role)}</p><small>${escapeHtml(data.profile.location)}</small></div></div></section><section class="section page-section"><div class="shell about-grid"><div><p class="eyebrow">FOCUS</p><h2>我关注的方向</h2></div><div class="about-content"><p class="large-copy">以 Java 后端为主线，同时具备 Vue 前端落地能力。我更关心系统是否真正解决业务问题，以及数据在整个流程中是否准确、可追溯。</p><div class="skill-grid"><article><span>01</span><h3>后端开发</h3><p>Spring Boot、REST API、权限、事务、业务状态和异常处理。</p></article><article><span>02</span><h3>数据与分析</h3><p>MySQL、SQL 查询、数据口径、报表和问题定位。</p></article><article><span>03</span><h3>前端交付</h3><p>Vue 3、响应式界面、后台工作台和业务交互。</p></article><article><span>04</span><h3>部署与验证</h3><p>Nginx、Linux、备份、发布检查和故障排查。</p></article></div></div></div></section>`;
  }

  function renderArticle(slug) {
    const post = data.posts.find((item) => item.slug === slug);
    if (!post) return renderNotFound();
    const headings = [...post.content.matchAll(/<h2 id="([^"]+)">([^<]+)<\/h2>/g)];
    document.title = `${post.title} · 小刘`;
    main.innerHTML = `<article class="article"><header class="article-header"><div class="shell article-shell"><a class="back-link" href="#/articles">← 返回文章列表</a><div class="post-meta"><span>${escapeHtml(post.category)}</span><time datetime="${post.date}">${formatDate(post.date)}</time><span>${post.readingMinutes} 分钟阅读</span></div><h1>${escapeHtml(post.title)}</h1><p>${escapeHtml(post.excerpt)}</p><div class="tag-list large">${post.tags.map((tag) => `<a href="#/articles?tag=${encodeURIComponent(tag)}">#${escapeHtml(tag)}</a>`).join('')}</div></div></header><div class="shell article-layout"><aside class="toc"><strong>本文目录</strong>${headings.map((heading) => `<a href="#${escapeHtml(heading[1])}">${escapeHtml(heading[2])}</a>`).join('')}</aside><div class="article-body">${post.content}<div class="article-end"><span>END</span><p>如果这篇文章对你有帮助，欢迎继续浏览我的项目和其他记录。</p><div><a class="primary-button" href="#/projects">查看项目</a><button class="secondary-button share-button" type="button">复制文章链接</button></div></div></div></div></article>`;
    enhanceArticle();
  }

  function renderNotFound() {
    document.title = '页面未找到 · 小刘';
    main.innerHTML = `<section class="not-found"><div class="shell"><span>404</span><h1>这页暂时不存在</h1><p>可能是地址发生了变化，或者内容还没有发布。</p><a class="primary-button" href="#/">返回首页</a></div></section>`;
  }

  function enhanceArticle() {
    document.querySelectorAll('.article-body pre').forEach((block) => {
      const button = document.createElement('button');
      button.className = 'copy-button'; button.type = 'button'; button.textContent = '复制';
      button.addEventListener('click', async () => { await navigator.clipboard.writeText(block.innerText); button.textContent = '已复制'; setTimeout(() => { button.textContent = '复制'; }, 1500); });
      block.appendChild(button);
    });
    const shareButton = document.querySelector('.share-button');
    shareButton?.addEventListener('click', async () => { await navigator.clipboard.writeText(window.location.href); shareButton.textContent = '链接已复制'; setTimeout(() => { shareButton.textContent = '复制文章链接'; }, 1500); });
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
    else if (section === 'resume') renderResume();
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
  window.addEventListener('hashchange', route);
  if (!location.hash) history.replaceState(null, '', `${rootUrl}#/`);
  route();
})();
