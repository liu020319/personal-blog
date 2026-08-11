/*
 * 这是博客唯一的内容配置文件。
 * 新增文章：复制 BLOG_DATA.posts 中的一项并修改字段。
 * 新增项目：复制 BLOG_DATA.projects 中的一项，url 填线上登录页地址。
 */
window.BLOG_DATA = {
  profile: {
    name: '小刘',
    role: 'Java 后端开发者 · Vue 全栈实践',
    location: '中国 · 武汉',
    intro: '关注业务闭环、数据可靠性与可维护的工程实现。这里记录我做过的项目、踩过的坑，以及每一次把复杂问题讲清楚的过程。',
    github: 'https://github.com/liu020319'
  },
  resume: {
    current: {
      version: '2026.08 · 当前版',
      updated: '2026-08-11',
      title: 'Java 后端开发公开简历',
      summary: '突出当前工作经历、Java 后端能力、数据报表实践，以及康联云从开发到生产上线的完整交付。',
      file: './resumes/current/xiaoliu-java-resume-current.pdf',
      available: true
    },
    history: [
      {
        version: '2026.08 · 当前版',
        stage: '工作能力整合阶段',
        date: '2026-08-11',
        change: '补强生产部署、业务闭环、权限隔离、消息可靠性和数据报表经验，求职方向进一步聚焦 Java 后端。',
        file: './resumes/current/xiaoliu-java-resume-current.pdf',
        available: true,
        current: true
      },
      {
        version: '2026.08 · 归档版',
        stage: '第一版完整工作简历',
        date: '2026-08-09',
        change: '首次系统整理工作经历、实习、毕业设计与个人全栈项目，形成一页式 Java 求职简历。',
        file: './resumes/archive/xiaoliu-java-resume-20260809.pdf',
        available: true,
        current: false
      },
      {
        version: '待补录',
        stage: '刚毕业阶段',
        date: '2025',
        change: '预留毕业求职简历位置。找到当时版本后原样归档，用于对比项目表达、技能重点和求职定位的变化。',
        file: '',
        available: false,
        current: false
      }
    ]
  },
  projects: [
    {
      id: 'kanglian-cloud',
      name: '康联云',
      subtitle: '家庭药事协同平台',
      description: '面向长期慢病家庭的双角色协同平台，覆盖用药方案、库存风险、购药申请、远程代购、物流、收货核验、资金台账与统计分析。',
      stack: ['Spring Boot', 'Vue 3', 'MySQL', 'Nginx'],
      status: '在线演示',
      url: 'https://xiaoliudev.com/kanglian-cloud/#/login',
      source: 'https://github.com/liu020319/DSMS',
      featured: true,
      accent: 'jade'
    }
  ],
  posts: [
    {
      slug: 'why-this-blog-is-static',
      title: '为什么我的个人博客选择纯静态方案',
      excerpt: '在 2 核 2G 的服务器条件下，把计算资源留给真正需要后端和数据库的业务系统。',
      date: '2026-08-11',
      category: '工程实践',
      tags: ['GitHub Pages', '性能', '部署'],
      readingMinutes: 5,
      featured: true,
      content: `
        <p class="lead">个人博客不一定需要再启动一套 Java 服务、数据库和管理后台。对目前的使用规模来说，静态站点是更稳妥的选择。</p>
        <h2 id="resource">把资源留给业务系统</h2>
        <p>现有云服务器承担了 Nginx、Java 后端和 MySQL。博客主要是公开内容展示，没有登录、支付或实时写入需求，静态 HTML、CSS 和 JavaScript 已经足够。这样访问文章时不会占用数据库连接，也不会和业务接口争抢内存。</p>
        <h2 id="benefits">静态方案带来的好处</h2>
        <ul><li><strong>轻：</strong>没有常驻博客进程，部署文件体积小。</li><li><strong>稳：</strong>页面文件可以直接缓存，不依赖数据库是否可用。</li><li><strong>安全：</strong>减少管理后台、插件和数据库暴露面。</li><li><strong>省心：</strong>提交到 GitHub 后即可发布，回滚也只是切换版本。</li></ul>
        <h2 id="features">静态不等于功能少</h2>
        <p>文章搜索、分类标签、归档、深色模式、阅读进度、RSS 和项目展示都可以在浏览器端完成。只有评论、订阅邮件等需要服务器写入的能力，才值得接入独立服务。</p>
        <blockquote>架构的价值不是组件越多越好，而是在当前约束下，用尽量少的复杂度解决真实问题。</blockquote>
        <h2 id="next">后续扩展</h2>
        <p>以后文章量增长，可以继续保持相同页面结构，只把内容生成环节交给静态站点生成器；访问侧仍然不需要额外服务器资源。</p>`
    },
    {
      slug: 'kanglian-cloud-project-retrospective',
      title: '康联云项目复盘：从功能集合到完整业务闭环',
      excerpt: '一次围绕家庭慢病用药场景的全栈实践：不仅把页面做出来，更要让申请、审批、代购、核验和库存真正连起来。',
      date: '2026-08-09',
      category: '项目复盘',
      tags: ['Spring Boot', 'Vue 3', 'MySQL'],
      readingMinutes: 8,
      featured: true,
      content: `
        <p class="lead">康联云不是一个简单的药品增删改查系统。它试图解决的是：家人不在身边时，如何共同完成用药管理、远程购药和收货核验。</p>
        <h2 id="problem">业务问题</h2>
        <p>长期用药会同时涉及方案、库存、申请、审批、购买、物流、收货和费用。如果这些信息分散在聊天记录和不同页面里，任何一个环节断开，都可能造成漏买、重复购买或对账困难。</p>
        <h2 id="roles">先把角色和任务理清</h2>
        <p>系统将使用者分为家庭协同端和安心用药端。前者负责配置、审批、代购和异常处置，后者负责查看计划、提交需求和核验收货。权限设计不再只看“能否打开页面”，还要看数据属于哪个家庭、当前业务走到哪一步。</p>
        <h2 id="loop">核心业务闭环</h2>
        <ol><li>安心用药成员提交需求并确认药品明细；</li><li>家庭管理员审批，形成代购订单；</li><li>记录实际价格、平台、物流和资金变化；</li><li>收货时核对数量、批准文号和包装；</li><li>核验通过后才更新库存，异常则进入处理流程。</li></ol>
        <h2 id="engineering">工程实现</h2>
        <p>后端采用 Spring Boot 和 MyBatis-Plus 承担认证、事务与业务规则，MySQL 保存可追溯数据；前端使用 Vue 3，将十多个功能按药事协同、购药履约、运营洞察和系统治理重新组织；Nginx 统一提供页面并转发 API。</p>
        <pre><code>浏览器 → Nginx → Vue 静态页面
              └→ /api → Spring Boot → MySQL</code></pre>
        <h2 id="lesson">最大的收获</h2>
        <p>系统的完成度不取决于页面数量，而取决于关键数据能否沿着完整流程可靠流转。业务状态、事务边界、异常补偿和最终验证，往往比单个接口本身更重要。</p>`
    },
    {
      slug: 'safe-release-checklist',
      title: '一次稳妥上线需要检查什么',
      excerpt: '打包成功只是开始。备份、配置、数据库迁移、服务状态和浏览器端验证共同构成上线证据。',
      date: '2026-08-07',
      category: '部署运维',
      tags: ['Nginx', 'MySQL', '发布检查'],
      readingMinutes: 6,
      featured: false,
      content: `
        <p class="lead">“代码能编译”与“线上业务可用”之间，还有一段必须认真走完的路。</p>
        <h2 id="before">发布前</h2>
        <ul><li>确认要发布的分支和文件范围，避免把本地测试数据带上去；</li><li>备份数据库、当前程序包、网页文件、上传文件和运行配置；</li><li>检查磁盘空间、端口占用以及 Nginx 配置；</li><li>把生产密码和账号初始化数据留在 Git 之外。</li></ul>
        <h2 id="during">发布中</h2>
        <p>数据库脚本要有明确顺序和失败停止条件。程序更新后，先观察启动日志与服务状态，再让入口流量进入新版本。遇到异常时，应优先恢复服务，不在生产环境里反复尝试不确定操作。</p>
        <h2 id="after">发布后</h2>
        <ol><li>检查前端首页和静态资源是否正常；</li><li>检查后端健康状态和关键接口；</li><li>使用浏览器完成真实登录；</li><li>验证一条最重要的业务链路；</li><li>确认日志没有持续异常，再结束发布。</li></ol>
        <h2 id="boundary">结论要有证据边界</h2>
        <p>有备份只能说明可以恢复，服务显示运行只能说明进程存在。只有数据库、接口和浏览器链路都验证后，才能说本次上线完成。</p>`
    },
    {
      slug: 'backend-troubleshooting-order',
      title: '后端问题排查：先确定范围，再深入代码',
      excerpt: '面对线上异常，先看影响范围、请求证据和系统状态，往往比立刻修改代码更有效。',
      date: '2026-08-05',
      category: 'Java 后端',
      tags: ['排障', '日志', 'SQL'],
      readingMinutes: 5,
      featured: false,
      content: `
        <p class="lead">有效排障的关键不是“猜得快”，而是不断缩小问题范围。</p>
        <h2 id="scope">一、确认影响范围</h2>
        <p>先确认是所有用户、某个角色、某类数据还是单一请求受影响，同时记录发生时间、操作步骤和预期结果。范围越明确，后续证据越容易对齐。</p>
        <h2 id="evidence">二、沿请求链路找证据</h2>
        <p>按 traceId 或时间窗口检查入口日志、请求参数、后端异常、实际 SQL、数据库结果和外部依赖状态。不要只看最后一条报错，更要找它之前发生了什么。</p>
        <h2 id="mitigate">三、先止损再修复</h2>
        <p>如果问题影响线上业务，优先通过回滚、关闭异常入口、限流或人工补偿恢复可用性。修复方案要覆盖根因，而不是只绕开当前样例。</p>
        <h2 id="verify">四、验证正常、异常和并发场景</h2>
        <p>修复后至少验证正常路径、边界输入、重复提交和并发条件，并观察日志与数据是否符合预期。最后记录根因和防复发措施。</p>`
    }
  ]
};
