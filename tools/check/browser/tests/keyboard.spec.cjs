const {test,expect,docs,paths,openNav,openPanorama,tabTo,transform,focusedNodeVisible,screenshot}=require('../helpers.cjs');

test('Tab order, filter Enter/Space and redraws retain visible focus',async({page},testInfo)=>{
  await openNav(page);
  for(const selector of ['a[href="panorama.html"]','a[href="https://github.com/gonglei007/GameDevMind"]','#search']) {
    await page.keyboard.press('Tab'); await expect(page.locator(selector)).toBeFocused();
  }
  await page.keyboard.type('网络');await expect(page.locator('#search')).toBeFocused();
  await page.keyboard.press('Control+A'); await page.keyboard.press('Backspace');
  for(const [label,predicate] of [['初级',d=>d.l===1],['中级',d=>d.l===2],['高级',d=>d.l===3],
    ['客户端',d=>d.r.split(',').includes('客户端')],['服务端',d=>d.r.split(',').includes('服务端')]]) {
    await page.keyboard.press('Tab');
    const button=page.getByRole('button',{name:label,exact:true}); await expect(button).toBeFocused();
    await page.keyboard.press('Enter');await expect(button).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.doc-card')).toHaveCount(docs.filter(predicate).length);
    await page.keyboard.press('Space'); await expect(button).toHaveAttribute('aria-pressed','false');
    await expect(button).toBeFocused();
  }
  await tabTo(page,'[data-focus-key="category-1"]'); await page.keyboard.press('Enter');
  await expect(page.locator('[data-focus-key="category-1"]')).toBeFocused();
  await expect(page.locator('.doc-card')).toHaveCount(docs.filter(d=>d.c===1).length);
  await page.keyboard.press('Tab'); await expect(page.locator('[data-focus-key="category-2"]')).toBeFocused();
  await page.keyboard.press('Shift+Tab');await expect(page.locator('[data-focus-key="category-1"]')).toBeFocused();
  await tabTo(page,'#search',true);await page.keyboard.type('不存在xyz');
  await tabTo(page,'[data-focus-key="path-a"]'); await page.keyboard.press('Space');
  await expect(page.locator('[data-focus-key="path-a"]')).toBeFocused();
  await page.keyboard.press('Space');await page.keyboard.press('Tab');await page.keyboard.press('Enter');
  await expect(page.locator('[data-focus-key="path-b"]')).toBeFocused();
  await tabTo(page,'#search',true);await page.keyboard.press('Control+A');await page.keyboard.press('Backspace');
  await expect(page.locator('.doc-card')).toHaveCount(paths.find(p=>p.id==='b').paths.length);
  await tabTo(page,'[data-focus-key="path-b"]');await page.keyboard.press('Enter');
  await expect(page.locator('.doc-card')).toHaveCount(docs.length);
  await expect(page.locator('[data-focus-key="path-b"]')).toBeFocused();
  expect(await page.evaluate(()=>{
    const r=document.activeElement.getBoundingClientRect();
    return r.top>=document.querySelector('.header').getBoundingClientRect().bottom && r.bottom<=innerHeight;
  })).toBe(true);
  await screenshot(page,testInfo,'learning-path-focus');
});

for(const width of [1440,390]) {
  test(`node keyboard traversal, activation, actions and shortcuts at width ${width}`,async({page},testInfo)=>{
    await page.setViewportSize({width,height:width===390?844:1000});await openPanorama(page);
    await tabTo(page,'#tabs .tab[data-module="0"]');await page.keyboard.press('Enter');
    await expect(page.locator('#tabs .tab[data-module="0"]')).toBeFocused();
    const count=docs.filter(d=>d.c===1).length;
    await expect(page.locator('.node:visible')).toHaveCount(count);
    await page.keyboard.press('Space');await tabTo(page,'.node');
    await expect(page.locator('.node.d0.m0')).toBeFocused();
    await expect(page.locator('.node[tabindex="0"]')).toHaveCount(1);
    await page.keyboard.press('End');await expect(page.locator('.node[data-name="计算机网络"]')).toBeFocused();
    await focusedNodeVisible(page);await screenshot(page,testInfo,'keyboard-node-focus');
    await page.keyboard.press('Home');await page.keyboard.press('ArrowRight');
    const parent=page.locator('.node[data-name="编程语言"]');await expect(parent).toBeFocused();
    await page.keyboard.press('ArrowLeft');await expect(parent).toHaveAttribute('aria-expanded','false');await expect(parent).toBeFocused();
    await page.keyboard.press('ArrowRight');await expect(parent).toHaveAttribute('aria-expanded','true');
    await page.keyboard.press('ArrowRight');await expect(page.locator('.node[data-name="编程语言基础概念"]')).toBeFocused();
    await page.keyboard.press('ArrowUp');await expect(parent).toBeFocused();
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');await page.keyboard.press('Space');
    await expect(page.locator('.node:visible')).toHaveCount(count);
    await page.keyboard.press('Tab');await expect(page.locator('#selected-link')).toBeFocused();
    const opened=page.waitForEvent('popup');await page.keyboard.press('Enter');
    const article=await opened;await expect(article.locator('body')).toContainText('编程语言基础概念');await article.close();
    await page.bringToFront();await page.keyboard.press('Shift+Tab');
    await expect(page.locator('.node[data-name="编程语言基础概念"]')).toBeFocused();
    await page.keyboard.press('ArrowLeft');await page.keyboard.press('Enter');
    await expect(parent).toBeFocused();await expect(parent).toHaveAttribute('aria-expanded','false');
    await page.keyboard.press('Space');await expect(parent).toHaveAttribute('aria-expanded','true');
    const initial=await transform(page);await page.keyboard.press('=');
    await expect.poll(async()=>(await transform(page)).scale).toBeGreaterThan(initial.scale);
    await page.keyboard.press('-');await expect.poll(async()=>(await transform(page)).scale).toBeCloseTo(initial.scale,4);
    for(const key of ['Control+-','Meta+-','Alt+-']) {
      const before=await transform(page);await page.keyboard.press(key);
      expect((await transform(page)).scale).toBe(before.scale);
    }
    for(const key of ['r','0']) {
      await page.keyboard.press(key);await expect(page.locator('.node:visible')).toHaveCount(docs.length);
      await expect(parent).toBeFocused();await focusedNodeVisible(page);
    }
    await page.keyboard.press('Tab');await page.keyboard.press('Tab');await expect(page.locator('#selected-toggle')).toBeFocused();
    await page.keyboard.press('Space');await expect(page.locator('#selected-toggle')).toBeFocused();
    await page.keyboard.press('r');await expect(parent).toBeFocused();
    for(let i=0;i<3;i++)await page.keyboard.press('Tab');
    await expect(page.locator('#btn-zoom-in')).toBeFocused();
    const before=await transform(page);await page.keyboard.press('Enter');await page.keyboard.press('Space');
    await expect.poll(async()=>(await transform(page)).scale).toBeGreaterThan(before.scale);
    await page.keyboard.press('Tab');await expect(page.locator('#btn-zoom-out')).toBeFocused();
    await page.keyboard.press('Enter');await page.keyboard.press('Tab');await page.keyboard.press('Enter');
    await expect(page.locator('#btn-reset')).toBeFocused();
    for(let i=0;i<3;i++)await page.keyboard.press('Shift+Tab');await expect(parent).toBeFocused();
  });
}
