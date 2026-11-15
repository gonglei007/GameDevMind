const {test,expect,docs,openNav,openPanorama,moduleFilter,transform,screenshot}=require('../helpers.cjs');

for(const viewport of [{width:320,height:740},{width:390,height:844},{width:844,height:390}]) {
  test(`mobile layout and touch controls at ${viewport.width}x${viewport.height}`,async({page},testInfo)=>{
    await page.setViewportSize(viewport); await openNav(page);
    const beginner=page.getByRole('button',{name:'初级',exact:true});
    await beginner.tap(); await expect(page.locator('.doc-card')).toHaveCount(docs.filter(d=>d.l===1).length);
    await beginner.tap();
    await page.getByRole('textbox').fill('客户端网络系统');
    const code=page.getByRole('link',{name:'📦 代码',exact:true});
    await expect(code).toBeVisible();
    expect((await code.boundingBox()).height).toBeGreaterThanOrEqual(44);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await screenshot(page,testInfo,'mobile-navigation');
    await code.tap(); await expect(page.locator('body')).toContainText('客户端网络系统');
    await page.goBack(); await page.getByRole('link',{name:'🗺️ 全景图'}).tap();
    await expect(page.locator('.node')).toHaveCount(docs.length);
    await moduleFilter(page,2,true);
    for(const name of ['放大','缩小','重置视图']) {
      const button=page.getByRole('button',{name,exact:true});
      expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(44);
    }
    const before=await transform(page);
    await page.getByRole('button',{name:'放大',exact:true}).tap();
    await expect.poll(async()=>(await transform(page)).scale).toBeGreaterThan(before.scale);
    await page.getByRole('button',{name:'缩小',exact:true}).tap();
    await expect.poll(async()=>(await transform(page)).x).toBeCloseTo(before.x,1);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await screenshot(page,testInfo,'mobile-panorama');
  });
}

test('native touch: swipe tabs, pan a node without folding, tap to toggle and open',async({page,context})=>{
  await openPanorama(page); await page.bringToFront();
  const cdp=await context.newCDPSession(page);
  const tabs=await page.locator('#tabs').boundingBox(),y=tabs.y+tabs.height/2;
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:300,y,id:0}]});
  for(const x of [240,180,120,80]) {
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y,id:0}]});
    await page.evaluate(()=>new Promise(requestAnimationFrame));
  }
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect.poll(()=>page.locator('#tabs').evaluate(el=>el.scrollLeft)).toBeGreaterThan(0);
  await moduleFilter(page,0,true);
  const count=docs.filter(d=>d.c===1).length;
  const root=page.locator('.node.d0.m0'),box=await root.boundingBox(),before=await transform(page);
  const x=box.x+box.width/2,ny=box.y+box.height/2;
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y:ny,id:0}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+40,y:ny+30,id:0}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await expect.poll(async()=>(await transform(page)).x-before.x).toBeCloseTo(40,1);
  await expect(page.locator('.node:visible')).toHaveCount(count);
  await root.tap(); await expect(page.locator('.node:visible')).toHaveCount(1);
  await expect(page.locator('.node:visible:not(.m0)')).toHaveCount(0);
  await page.getByRole('button',{name:'展开节点',exact:true}).tap();
  await expect(page.locator('.node:visible')).toHaveCount(count);
  const opened=page.waitForEvent('popup');
  await page.getByRole('link',{name:'打开文档 ↗',exact:true}).tap();
  const article=await opened; await expect(article.locator('body')).toContainText('基础能力');
  await article.close();
});

test('native translated pinch anchors correctly and continues with the remaining finger',async({page,context})=>{
  await openPanorama(page); await moduleFilter(page,0,true);
  const cdp=await context.newCDPSession(page),wrap=await page.locator('#wrap').boundingBox();
  const y=wrap.y+wrap.height*0.4,before=await transform(page);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:120,y,id:0},{x:220,y,id:1}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:100,y:y+30,id:0},{x:260,y:y+30,id:1}]});
  await expect.poll(async()=>(await transform(page)).scale/before.scale).toBeCloseTo(1.6,2);
  const pinched=await transform(page);
  expect(pinched.x).toBeCloseTo(180-(170-before.x)*1.6,1);
  expect(pinched.y).toBeCloseTo(y+30-wrap.y-(y-wrap.y-before.y)*1.6,1);
  // CDP touchEnd identifies the finger being removed; id:1 remains active.
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[{x:100,y:y+30,id:0}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:280,y:y+50,id:1}]});
  await expect.poll(async()=>(await transform(page)).x-pinched.x).toBeCloseTo(20,1);
  await expect.poll(async()=>(await transform(page)).y-pinched.y).toBeCloseTo(20,1);
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
});
