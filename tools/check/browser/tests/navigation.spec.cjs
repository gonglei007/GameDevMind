const {test,expect,docs,stats,paths,modules,openNav} = require('../helpers.cjs');

test('search handles whitespace, case, no results and clearing', async ({page}) => {
  await openNav(page);
  const search=page.getByRole('textbox',{name:'搜索文档标题…'});
  for(const query of ['客户端网络系统',' 网络 ','c#','不存在xyz','<img src=x onerror=alert(1)>','   ']) {
    await search.fill(query);
    const expected=docs.filter(d=>d.t.toLowerCase().includes(query.trim().toLowerCase())).length;
    await expect(page.locator('.doc-card')).toHaveCount(expected);
    if(!expected) await expect(page.getByText('没有匹配的文档 😕',{exact:true})).toBeVisible();
    await expect(search).toBeFocused();
  }
  await expect(page.locator('#stats')).toContainText(`全库 ${stats.documents} 篇`);
});

test('category, level, role and learning-path filters toggle and intersect', async ({page}) => {
  await openNav(page);
  for(const [label,predicate] of [
    ['初级',d=>d.l===1],['中级',d=>d.l===2],['高级',d=>d.l===3],
    ['客户端',d=>d.r.split(',').includes('客户端')],['服务端',d=>d.r.split(',').includes('服务端')],
  ]) {
    const button=page.getByRole('button',{name:label,exact:true});
    await button.click(); await expect(button).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.doc-card')).toHaveCount(docs.filter(predicate).length);
    await button.click(); await expect(button).toHaveAttribute('aria-pressed','false');
    await expect(page.locator('.doc-card')).toHaveCount(docs.length);
  }
  for(const label of ['初级','中级']) await page.getByRole('button',{name:label,exact:true}).click();
  await expect(page.locator('.doc-card')).toHaveCount(docs.filter(d=>[1,2].includes(d.l)).length);
  for(const label of ['初级','中级']) await page.getByRole('button',{name:label,exact:true}).click();
  for(let i=0;i<modules.length;i++) {
    const tab=page.locator('.cat-tab').nth(i+1);
    await tab.click(); await expect(tab).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.doc-card')).toHaveCount(docs.filter(d=>d.c===i+1).length);
  }
  await page.locator('.cat-tab').first().click();
  for(const p of paths) {
    const card=page.locator(`[data-focus-key="path-${p.id}"]`);
    await card.click(); await expect(card).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.doc-card')).toHaveCount(p.paths.length);
    await expect(page.locator('#stats')).toContainText(p.title);
    await card.click(); await expect(page.locator('.doc-card')).toHaveCount(docs.length);
  }
  await page.getByRole('button',{name:'中级',exact:true}).click();
  await page.getByRole('button',{name:'客户端',exact:true}).click();
  await page.locator('.cat-tab').nth(3).click();
  await page.getByRole('textbox').fill('网络');
  await expect(page.getByRole('link',{name:'客户端网络系统',exact:true})).toBeVisible();
  await expect(page.locator('.doc-card')).toHaveCount(docs.filter(d=>d.l===2 && d.c===3 && d.r.split(',').includes('客户端') && d.t.includes('网络')).length);
});

test('document, example, guide and panorama destinations are usable', async ({page}) => {
  await openNav(page);
  await page.getByRole('textbox').fill('客户端网络系统');
  await page.getByRole('link',{name:'客户端网络系统',exact:true}).click();
  await expect(page).toHaveURL(/3\.1\.4\..*\.md$/);
  await expect(page.locator('body')).toContainText('客户端网络系统');
  await page.goBack();
  await page.getByRole('textbox').fill('客户端网络系统');
  await page.getByRole('link',{name:'📦 代码',exact:true}).click();
  await expect(page).toHaveURL(/\/code\/.*\/$/);
  await expect(page.locator('body')).toContainText('客户端网络系统');
  await page.goBack();
  await page.getByRole('link',{name:'推荐阅读路径.md',exact:true}).click();
  await expect(page.locator('body')).toContainText('推荐阅读路径');
  await page.goBack();
  await expect(page.getByRole('link',{name:'← 返回仓库'})).toHaveAttribute('href','https://github.com/gonglei007/GameDevMind');
  await page.getByRole('link',{name:'🗺️ 全景图'}).click();
  await expect(page.locator('.node')).toHaveCount(docs.length);
  await page.getByRole('link',{name:'← 返回导航'}).click();
  await expect(page.locator('.cat-tab')).toHaveCount(7);
});
