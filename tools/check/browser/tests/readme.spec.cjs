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
const summaries=['展开知识全景预览','更多示例与案例','邮箱联系、项目资料、贡献者与鸣谢'];
const imageAlts=['AI 游戏开发：人工决策、AI 执行与验证','基础能力','技术能力','研发能力','生产能力','管理能力','运营能力',
  '游戏开发技术图谱全景预览','Vika','顶游社','GameDevMind Logo'];
const localLinks=[
  ['阅读说明','mds/阅读说明.md'],['文档索引','INDEX.md'],['关键词索引','KEYWORDS.md'],
  ['代码示例','code/README.md'],['案例与诊断练习','cases/README.md'],['AI 研发与应用资料中心','docs/AI/README.md'],
  ['GGFramework 实践导读','docs/工程实践/GGFramework.md'],
  ['内存池','code/gamedevmind/1.基础能力/1.1.2.C++语言/memory_pool/'],
  ['客户端网络生命周期','code/gamedevmind/3.研发能力/3.1.4.客户端网络系统/client_network/'],
  ['四叉树','code/gamedevmind/1.基础能力/1.2.2.数据结构/quadtree/'],
  ['帧同步 vs 状态同步','code/gamedevmind/2.技术能力/2.2.1.网络与通信/network_sync/'],
  ['开放世界卡顿复核','cases/drawcall-optimization.md'],['贡献指南','CONTRIBUTING.md'],['更新记录','HISTORY.md'],
];
async function audit(page,testInfo,url) {
  await page.goto(url,{waitUntil:'domcontentloaded'});
  const article=page.getByRole('article');
  await expect(article.getByRole('heading',{name:'游戏开发 · 技术图谱',exact:true})).toBeVisible({timeout:45000});
  await expect(article.locator('details')).toHaveCount(3);
  for(const summary of summaries) {
    const control=article.locator('summary').filter({hasText:summary});
    const detail=control.locator('..');
    await expect(detail).toHaveJSProperty('open',false);
    await control.click();await expect(detail).toHaveJSProperty('open',true);
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
  for(const [name,destination] of localLinks) {
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
  await screenshot(page,testInfo,'readme-desktop',article);
  await page.setViewportSize({width:390,height:844});
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
  await page.getByRole('article').getByRole('link',{name:'Core 基础能力实践',exact:true}).first().click();
  const core=page.getByRole('article');
  await expect(core.getByRole('heading',{name:'GGFramework Core 基础能力实践：状态、订阅、复用与退出',exact:true})).toBeVisible({timeout:45000});
  await expect(core.getByRole('heading',{name:'退出生命周期：标志、任务与实例分别处理',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'ggframework-core-mobile',core);
  await page.setViewportSize({width:1440,height:1000});
  await screenshot(page,testInfo,'ggframework-core-desktop',core);
  await page.setViewportSize({width:390,height:844});
  await core.getByRole('link',{name:'客户端底层通用系统',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'客户端底层通用系统',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  await expect(page.getByRole('article').getByRole('heading',{name:'从知识点到 Unity 工程：GGFramework 实践导读',exact:true})).toBeVisible({timeout:45000});
  await page.getByRole('article').getByRole('link',{name:'用户与 SDK 接入实践',exact:true}).first().click();
  const users=page.getByRole('article');
  await expect(users.getByRole('heading',{name:'GGFramework 用户与 SDK 接入实践：登录状态与支付验证边界',exact:true})).toBeVisible({timeout:45000});
  await expect(users.getByRole('heading',{name:'支付回调与服务端验单',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'ggframework-user-sdk-mobile',users);
  await page.setViewportSize({width:1440,height:1000});
  await screenshot(page,testInfo,'ggframework-user-sdk-desktop',users);
  await page.setViewportSize({width:390,height:844});
  await users.getByRole('link',{name:'用户与帐号系统',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'用户与帐号系统',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'支付与变现',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'支付与变现',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  await expect(page.getByRole('article').getByRole('heading',{name:'从知识点到 Unity 工程：GGFramework 实践导读',exact:true})).toBeVisible({timeout:45000});
  await page.getByRole('article').getByRole('link',{name:'UI 管理实践',exact:true}).first().click();
  const ui=page.getByRole('article');
  await expect(ui.getByRole('heading',{name:'GGFramework UI 管理实践：页面栈、窗口归属与生命周期',exact:true})).toBeVisible({timeout:45000});
  await expect(ui.getByRole('heading',{name:'NGUI、UGUI 与 Demo 的支持状态',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'ggframework-ui-mobile',ui);
  await page.setViewportSize({width:1440,height:1000});
  await screenshot(page,testInfo,'ggframework-ui-desktop',ui);
  await page.setViewportSize({width:390,height:844});
  await ui.getByRole('link',{name:'UI系统',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'UI系统',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  await expect(page.getByRole('article').getByRole('heading',{name:'从知识点到 Unity 工程：GGFramework 实践导读',exact:true})).toBeVisible({timeout:45000});
  await page.getByRole('article').getByRole('link',{name:'资源管理实践',exact:true}).first().click();
  const resources=page.getByRole('article');
  await expect(resources.getByRole('heading',{name:'GGFramework 资源管理实践：加载来源与释放责任',exact:true})).toBeVisible({timeout:45000});
  await expect(resources.getByRole('heading',{name:'引用计数：缓存查询不等于取得所有权',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'ggframework-resource-mobile',resources);
  await page.setViewportSize({width:1440,height:1000});
  await screenshot(page,testInfo,'ggframework-resource-desktop',resources);
  await page.setViewportSize({width:390,height:844});
  await resources.getByRole('link',{name:'客户端底层通用系统',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'客户端底层通用系统',exact:true})).toBeVisible({timeout:45000});
  await page.goBack();
  await page.getByRole('article').getByRole('link',{name:'GGFramework 实践导读',exact:true}).click();
  await expect(page.getByRole('article').getByRole('heading',{name:'从知识点到 Unity 工程：GGFramework 实践导读',exact:true})).toBeVisible({timeout:45000});
  await page.getByRole('article').getByRole('link',{name:'客户端网络实践样板',exact:true}).first().click();
  const practice=page.getByRole('article');
  await expect(practice.getByRole('heading',{name:'GGFramework 客户端网络实践：异常反馈与重试',exact:true})).toBeVisible({timeout:45000});
  await expect(practice.getByRole('heading',{name:'两条实现路径',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await screenshot(page,testInfo,'ggframework-network-mobile',practice);
  await practice.getByRole('link',{name:'客户端网络系统',exact:true}).first().click();
  await expect(page.getByRole('article').getByRole('heading',{name:'客户端网络系统',exact:true})).toBeVisible({timeout:45000});
});

// A PR's candidate README is rendered above; the public homepage represents main.
// Do not mistake an old main homepage for validation of a pull request's content.
if(!process.env.CI || process.env.GITHUB_EVENT_NAME==='push') {
  test('public repository homepage has the same required presentation',async({page},testInfo)=>{
    test.setTimeout(180000);await audit(page,testInfo,repo);
  });
}
