// This suite uses real GitHub rendering and media. No DOM/HTML/image response mocks.
const {test,expect}=require('@playwright/test');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const {root,screenshot}=require('../helpers.cjs');
const repository=process.env.GITHUB_REPOSITORY || 'gonglei007/GameDevMind';
const ref=process.env.README_REF || execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
if(!/^[\w.-]+\/[\w.-]+$/.test(repository) || !/^[a-f0-9]{40,64}$/.test(ref))throw new Error('Expected repository owner/name and an immutable commit SHA');
const committed=execFileSync('git',['show',`${ref}:README.md`],{cwd:root,encoding:'utf8'});
if(committed.replace(/\r\n/g,'\n')!==fs.readFileSync(path.join(root,'README.md'),'utf8').replace(/\r\n/g,'\n'))throw new Error('README.md differs from README_REF: the live GitHub test must match the checked-out README');
const repo=`https://github.com/${repository}`;
const exampleSummary='展开精选示例与案例';
const featureTitle='GGFramework：把知识点放进真实工程';
const summaries=['展开知识全景预览',exampleSummary,'邮箱联系、项目资料、贡献者与鸣谢'];
const exampleNames=['内存池','客户端网络生命周期','SLG 循环引用','MOBA 角色回弹复核','四叉树','帧同步 vs 状态同步','开放世界卡顿复核'];
const imageAlts=['AI 游戏开发：人工决策、AI 执行与验证','基础能力','技术能力','研发能力','生产能力','管理能力','运营能力',
  '游戏开发技术图谱全景预览','Vika','顶游社','GameDevMind Logo'];
const localLinks=[
  ['阅读说明','mds/阅读说明.md'],['文档索引','INDEX.md'],['关键词索引','KEYWORDS.md'],
  ['代码示例','code/README.md'],['案例与诊断练习','cases/README.md'],['AI 研发与应用资料中心','docs/AI/README.md'],
  ['GGFramework 实践导读','docs/工程实践/GGFramework.md'],
  ['运行 Demo 与查看验证记录','docs/工程实践/GGFrameworkUnity验证记录.md'],
  ['自动化回归与 CI 复现','docs/工程实践/GGFramework自动化回归与CI.md'],
  ['内存池','code/gamedevmind/1.基础能力/1.1.2.C++语言/memory_pool/'],
  ['客户端网络生命周期','code/gamedevmind/3.研发能力/3.1.4.客户端网络系统/client_network/'],
  ['SLG 循环引用','cases/memory-leak-slg.md'],['MOBA 角色回弹复核','cases/network-reconciliation.md'],
  ['四叉树','code/gamedevmind/1.基础能力/1.2.2.数据结构/quadtree/'],
  ['帧同步 vs 状态同步','code/gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync/'],
  ['开放世界卡顿复核','cases/drawcall-optimization.md'],['贡献指南','CONTRIBUTING.md'],['更新记录','HISTORY.md'],
];
const seriesGuideTitle='从知识点到 Unity 工程：GGFramework 实践导读';
const commonNode={label:'客户端底层通用系统',path:'mds/3.研发能力/3.1.1.客户端底层通用系统.md'};
const updateNode={label:'产品热更新',path:'mds/6.运营能力/6.2.3.产品热更新.md'};
const practices=[
  {label:'Core 基础能力实践',file:'GGFrameworkCore基础能力实践.md',title:'GGFramework Core 基础能力实践：状态、订阅、复用与退出',
    section:'退出生命周期：标志、任务与实例分别处理',image:'ggframework-core',nodes:[commonNode]},
  {label:'资源管理实践',file:'GGFramework资源管理实践.md',title:'GGFramework 资源管理实践：加载来源与释放责任',
    section:'引用计数：缓存查询不等于取得所有权',image:'ggframework-resource',nodes:[commonNode,updateNode]},
  {label:'客户端网络实践',file:'GGFramework客户端网络实践.md',title:'GGFramework 客户端网络实践：异常反馈与重试',
    section:'两条实现路径',image:'ggframework-network',nodes:[{label:'客户端网络系统',path:'mds/3.研发能力/3.1.4.客户端网络系统.md'}]},
  {label:'UI 管理实践',file:'GGFrameworkUI管理实践.md',title:'GGFramework UI 管理实践：页面栈、窗口归属与生命周期',
    section:'NGUI、UGUI 与 Demo 的支持状态',image:'ggframework-ui',nodes:[{label:'UI系统',path:'mds/3.研发能力/3.1.6.UI系统.md'},commonNode]},
  {label:'用户与 SDK 接入实践',file:'GGFramework用户与SDK接入实践.md',title:'GGFramework 用户与 SDK 接入实践：登录状态与支付验证边界',
    section:'支付回调与服务端验单',image:'ggframework-user-sdk',nodes:[{label:'用户与帐号系统',path:'mds/3.研发能力/3.3.5.用户与帐号系统.md'},
      {label:'支付与变现',path:'mds/6.运营能力/6.3.2.帐号与支付.md'}]},
  {label:'Lua 与热更新实践',file:'GGFrameworkLua与热更新实践.md',title:'GGFramework Lua 与热更新实践：脚本加载、互调与释放',
    section:'本地执行与生产热更新的边界',image:'ggframework-lua',nodes:[updateNode,commonNode]},
];
async function assertExamples(article,open) {
  for(const name of exampleNames) {
    const link=article.getByRole('link',{name,exact:true,includeHidden:true});
    await expect(link).toHaveCount(1);
    if(open)await expect(link).toBeVisible();
    else await expect(link).toBeHidden();
  }
}
async function assertFeature(article) {
  await expect(article.getByRole('heading',{name:featureTitle,exact:true})).toBeVisible();
  for(const name of ['GGFramework 实践导读','运行 Demo 与查看验证记录','自动化回归与 CI 复现',...practices.map(p=>p.label)]) {
    const link=article.getByRole('link',{name,exact:true});
    await expect(link).toHaveCount(1);await expect(link).toBeVisible();
  }
}
async function committedPath(page,destination) {
  await expect.poll(()=>decodeURIComponent(new URL(page.url()).pathname)).toBe(`/${repository}/blob/${ref}/${destination}`);
}
async function practiceArticle(page,practice) {
  await committedPath(page,'docs/工程实践/'+practice.file);
  const article=page.getByRole('article');
  for(const name of [practice.title,practice.section,'适用条件','验证方法与证据边界']) {
    await expect(article.getByRole('heading',{name,exact:true})).toBeVisible({timeout:45000});
  }
  for(const [label,anchor] of [['适用环境','适用条件'],['源码基线','固定源码基线'],['证据分层','验证方法与证据边界']]) {
    const href=await article.getByRole('link',{name:label,exact:true}).first().getAttribute('href');
    const target=new URL(href,repo);
    expect(target.origin).toBe('https://github.com');
    expect(decodeURIComponent(target.pathname)).toBe(`/${repository}/blob/${ref}/docs/工程实践/GGFramework.md`);
    expect(decodeURIComponent(target.hash)).toBe('#'+anchor);
  }
  return article;
}
async function auditSeries(page,testInfo) {
  for(const practice of practices) {
    await committedPath(page,'docs/工程实践/GGFramework.md');
    const guide=page.getByRole('article');
    await expect(guide.getByRole('heading',{name:seriesGuideTitle,exact:true})).toBeVisible({timeout:45000});
    const entry=guide.getByRole('link',{name:practice.label,exact:true});
    await expect(entry).toHaveCount(1);
    await entry.click();
    const article=await practiceArticle(page,practice);
    for(const [width,height,suffix] of [[390,844,'mobile'],[1440,1000,'desktop']]) {
      await page.setViewportSize({width,height});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      await screenshot(page,testInfo,practice.image+'-'+suffix,article);
    }
    await page.setViewportSize({width:390,height:844});
    for(const node of practice.nodes) {
      await article.getByRole('link',{name:node.label,exact:true}).first().click();
      await committedPath(page,node.path);
      const knowledge=page.getByRole('article');
      await expect(knowledge.getByRole('heading',{name:node.label,exact:true})).toBeVisible({timeout:45000});
      const backlink=knowledge.getByRole('link',{name:'GGFramework '+practice.label,exact:true});
      await expect(backlink).toHaveCount(1);
      await backlink.click();
      await practiceArticle(page,practice);
    }
    // Check the common boundary anchor with a real click, then return via the footer.
    await article.getByRole('link',{name:'证据分层',exact:true}).first().click();
    await committedPath(page,'docs/工程实践/GGFramework.md');
    await expect(page.getByRole('article').getByRole('heading',{name:'验证方法与证据边界',exact:true})).toBeVisible({timeout:45000});
    await page.goBack();
    await practiceArticle(page,practice);
    await article.getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  }
  await committedPath(page,'docs/工程实践/GGFramework.md');
  await expect(page.getByRole('article').getByRole('heading',{name:seriesGuideTitle,exact:true})).toBeVisible({timeout:45000});
}
async function audit(page,testInfo,url) {
  await page.goto(url,{waitUntil:'domcontentloaded'});
  const article=page.getByRole('article');
  await expect(article.getByRole('heading',{name:'游戏开发 · 技术图谱',exact:true})).toBeVisible({timeout:45000});
  await assertFeature(article);
  await assertExamples(article,false);
  const headings=await article.getByRole('heading',{level:2}).allTextContents();
  expect(headings.indexOf(featureTitle)).toBeGreaterThan(headings.indexOf('六大核心能力域'));
  expect(headings.indexOf(featureTitle)).toBeLessThan(headings.indexOf('AI 研发与应用'));
  const ids=await article.locator('a[id]').evaluateAll(anchors=>anchors.map(a=>a.id));
  for(const id of ['可立即使用的资源','精选代码示例','精选实战案例','ggframework-工程实践']) {
    expect(ids.some(value=>value===id || value==='user-content-'+id),id+' compatibility anchor').toBe(true);
  }
  await expect(article.locator('details')).toHaveCount(3);
  for(const summary of summaries) {
    const control=article.locator('summary').filter({hasText:summary});
    const detail=control.locator('..');
    await expect(detail).toHaveJSProperty('open',false);
    await control.click();await expect(detail).toHaveJSProperty('open',true);
    if(summary===exampleSummary)await assertExamples(article,true);
    await control.click();await expect(detail).toHaveJSProperty('open',false);
    await control.click();await expect(detail).toHaveJSProperty('open',true);
  }
  await expect(article.locator('img')).toHaveCount(imageAlts.length+3);
  await expect(article.locator('details').last().getByRole('link',{name:'gonglei@gltop.com',exact:true}))
    .toHaveAttribute('href','mailto:gonglei@gltop.com');
  for(const alt of imageAlts) {
    const img=article.getByRole('img',{name:alt,exact:true});
    await img.scrollIntoViewIfNeeded();
    await expect.poll(()=>img.evaluate(i=>i.complete && i.naturalWidth>0),{timeout:45000,message:`Missing README image: ${alt}`}).toBe(true);
    await expect(img).toBeVisible();
  }
  for(const [name,destination] of [...localLinks,...practices.map(p=>[p.label,'docs/工程实践/'+p.file])]) {
    const href=await article.getByRole('link',{name,exact:true}).getAttribute('href');
    const target=new URL(href,repo);
    expect(target.origin,name).toBe('https://github.com');
    expect(target.pathname.startsWith('/'+repository+'/'),name).toBe(true);
    expect(decodeURIComponent(target.pathname).replace(/\/$/,''),name)
      .toMatch(new RegExp('/'+destination.replace(/\/$/,'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'));
  }
  for(let i=0;i<6;i++) {
    const name=imageAlts[i+1];
    const link=article.getByRole('link',{name:`${i+1}. ${name}`,exact:true});
    expect(decodeURIComponent(new URL(await link.getAttribute('href'),repo).pathname)).toContain(`/mds/${i+1}.${name}/${i+1}.${name}.md`);
  }
  await expect(article.getByRole('link',{name:'交互式导航',exact:true})).toHaveAttribute('href','https://gonglei007.github.io/GameDevMind/nav/');
  await expect(article.getByRole('link',{name:'交互式知识全景',exact:true})).toHaveAttribute('href','https://gonglei007.github.io/GameDevMind/nav/panorama.html');
  for(const name of ['新人入门','研发实战','上线运营']) {
    const href=await article.getByRole('link',{name,exact:true}).getAttribute('href');
    expect(decodeURIComponent(new URL(href,repo).pathname)).toContain('/mds/topics/推荐阅读路径.md');
    expect(new URL(href,repo).hash).not.toBe('');
  }
  const exampleControl=article.locator('summary').filter({hasText:exampleSummary});
  await exampleControl.click();await assertExamples(article,false);
  await screenshot(page,testInfo,'readme-desktop',article);
  await page.setViewportSize({width:390,height:844});
  await assertFeature(article);
  await exampleControl.click();await assertExamples(article,true);
  await exampleControl.click();await assertExamples(article,false);
  for(const alt of imageAlts) {
    const img=article.getByRole('img',{name:alt,exact:true});
    const geometry=await img.evaluate(i=>{const r=i.getBoundingClientRect();return {w:r.width,h:r.height,nw:i.naturalWidth,nh:i.naturalHeight};});
    expect(geometry.w).toBeGreaterThan(0);expect(geometry.h).toBeGreaterThan(0);
    expect(Math.abs(geometry.w/geometry.h/(geometry.nw/geometry.nh)-1),alt+' aspect ratio').toBeLessThan(0.03);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'readme-mobile',article);
  const badges=await article.locator('img').evaluateAll(imgs=>imgs.filter(i=>['GitHub Stars','GitHub Forks','Contributors'].includes(i.alt)).map(i=>({alt:i.alt,src:i.getAttribute('data-canonical-src')||i.src,href:i.closest('a')?.href,loaded:i.complete && i.naturalWidth>0})));
  expect(badges).toHaveLength(3);
  for(const badge of badges) {
    expect(badge.src).toMatch(/^https:\/\/img\.shields\.io\/github\/(stars|forks|contributors)\//);
    expect(badge.href).toMatch(new RegExp('^'+repo.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'/'));
  }
  await testInfo.attach('external-badges',{body:JSON.stringify(badges,null,2),contentType:'application/json'});
}

test('commit README: images, disclosures, important entry points and mobile geometry',async({page},testInfo)=>{
  test.setTimeout(180000);
  await audit(page,testInfo,`${repo}/blob/${ref}/README.md`);
  const article=page.getByRole('article');
  await article.locator('a').filter({has:page.getByRole('img',{name:imageAlts[0],exact:true})}).click();
  await expect(page).toHaveURL(/\/docs\/AI\/README\.md$/);
  await expect(page.getByRole('article').getByRole('heading',{name:'AI 研发与应用',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'新人入门',exact:true}).click();
  await expect.poll(()=>decodeURIComponent(new URL(page.url()).pathname)).toContain('/mds/topics/推荐阅读路径.md');
  await expect(page.getByRole('article').getByRole('heading',{name:/路径 A/})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  await expect(page.getByRole('article').getByRole('heading',{name:'从知识点到 Unity 工程：GGFramework 实践导读',exact:true})).toBeVisible({timeout:45000});
  await auditSeries(page,testInfo);
  await page.getByRole('article').getByRole('link',{name:'返回首页',exact:true}).click();
  await committedPath(page,'README.md');
  await expect(page.getByRole('article').getByRole('heading',{name:featureTitle,exact:true})).toBeInViewport({timeout:45000});
  // Old article footers still target this alias; verify the real GitHub anchor jump.
  await page.goto(`${repo}/blob/${ref}/README.md#${encodeURIComponent('可立即使用的资源')}`,{waitUntil:'domcontentloaded'});
  await expect(page.getByRole('article').getByRole('heading',{name:featureTitle,exact:true})).toBeInViewport({timeout:45000});
});

// A PR's candidate README is rendered above; the public homepage represents main.
// Do not mistake an old main homepage for validation of a pull request's content.
if(!process.env.CI || process.env.GITHUB_EVENT_NAME==='push') {
  test('public repository homepage has the same required presentation',async({page},testInfo)=>{
    test.setTimeout(180000);await audit(page,testInfo,repo);
  });
}
