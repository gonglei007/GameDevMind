const {test,expect,docs,modules,openPanorama,moduleFilter,transform,screenshot} = require('../helpers.cjs');
const visibleEdges=page=>page.locator('.edge-line').evaluateAll(els=>els.filter(el=>getComputedStyle(el).display!=='none').length);

test('all six module filters survive root collapse and expansion', async ({page},testInfo) => {
  await openPanorama(page);
  for(let i=0;i<modules.length;i++) {
    await moduleFilter(page,i);
    const count=docs.filter(d=>d.c===i+1).length;
    await expect.poll(()=>visibleEdges(page)).toBe(count-1);
    await page.locator(`.node.d0.m${i}`).click();
    await expect(page.locator('.node:visible')).toHaveCount(1);
    await expect(page.locator(`.node:visible:not(.m${i})`)).toHaveCount(0);
    await expect.poll(()=>visibleEdges(page)).toBe(0);
    await page.getByRole('button',{name:'展开节点',exact:true}).click();
    await expect(page.locator('.node:visible')).toHaveCount(count);
    await expect.poll(()=>visibleEdges(page)).toBe(count-1);
  }
  await page.getByRole('button',{name:'重置视图',exact:true}).click();
  await expect(page.locator('.node:visible')).toHaveCount(docs.length);
  await expect(page.locator('#tabs .tab').first()).toHaveAttribute('aria-pressed','true');
  await moduleFilter(page,0);
  await screenshot(page,testInfo,'desktop-module');
});

test('nested nodes toggle; parent and leaf double clicks open once without folding', async ({page}) => {
  await openPanorama(page); await moduleFilter(page,0);
  const count=docs.filter(d=>d.c===1).length;
  const children=docs.filter(d=>d.parent===docs.find(d=>d.t==='编程语言').p).length;
  await page.locator('.node[data-name="编程语言"]').click();
  await expect(page.locator('.node:visible')).toHaveCount(count-children);
  await page.getByRole('button',{name:'展开节点',exact:true}).click();
  await expect(page.locator('.node:visible')).toHaveCount(count);
  const popups=[]; page.on('popup',popup=>popups.push(popup));
  for(const name of ['基础能力','C#语言']) {
    const opened=page.waitForEvent('popup');
    await page.locator(`.node[data-name="${name}"]`).dblclick({delay:100});
    const popup=await opened;
    const path=docs.find(d=>d.t===name).p;
    await expect.poll(()=>decodeURIComponent(new URL(popup.url()).pathname)).toBe('/'+path);
    await expect(popup.locator('body')).toContainText(name);
    await popup.close();
    await expect(page.locator('.node:visible')).toHaveCount(count);
  }
  expect(popups).toHaveLength(2);
});

test('dragging, wheel zoom and zoom buttons preserve a usable view', async ({page}) => {
  await openPanorama(page); await moduleFilter(page,2);
  const box=await page.locator('#wrap').boundingBox(),before=await transform(page);
  await page.mouse.move(box.x+20,box.y+20); await page.mouse.down();
  await page.mouse.move(box.x+70,box.y+60); await page.mouse.up();
  await expect.poll(async()=>(await transform(page)).x-before.x).toBeCloseTo(50,1);
  await page.mouse.wheel(0,-100);
  await expect.poll(async()=>(await transform(page)).scale).toBeGreaterThan(before.scale);
  const zoomed=await transform(page);
  await page.getByRole('button',{name:'放大',exact:true}).click();
  await expect.poll(async()=>(await transform(page)).scale).toBeGreaterThan(zoomed.scale);
  await page.getByRole('button',{name:'缩小',exact:true}).click();
  await expect.poll(async()=>(await transform(page)).scale).toBeCloseTo(zoomed.scale,4);
});
