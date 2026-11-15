const base = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const catalog = vm.runInNewContext(fs.readFileSync(path.join(root,'nav/content-data.js'),'utf8') +
  '\nJSON.stringify({docs:DOCS,stats:CONTENT_STATS,paths:LEARNING_PATHS.map(p=>({...p,paths:[...p.paths]}))})');
const {docs,stats,paths} = JSON.parse(catalog);
const modules = ['基础能力','技术能力','研发能力','生产能力','管理能力','运营能力'];
const test = base.test.extend({
  page: async ({page}, use) => {
    const errors=[];
    page.on('pageerror', error=>errors.push(error.message));
    await use(page);
    base.expect(errors,'Application JavaScript errors').toEqual([]);
  },
});
const {expect}=base;
async function openNav(page) {
  await page.goto('/nav/index.html');
  await expect(page.locator('.doc-card')).toHaveCount(docs.length);
}
async function openPanorama(page) {
  await page.goto('/nav/panorama.html');
  await expect(page.locator('.node')).toHaveCount(docs.length);
  // Wait for the initial two animation frames, not an arbitrary delay.
  await expect(page.locator('#canvas')).toHaveAttribute('style',/scale\(/);
}
async function moduleFilter(page,index, touch=false) {
  const button=page.locator('#tabs .tab').filter({hasText:modules[index]});
  await button[touch?'tap':'click']();
  await expect(button).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.node:visible')).toHaveCount(docs.filter(d=>d.c===index+1).length);
}
async function tabTo(page, selector, reverse=false) {
  for(let i=0;i<docs.length*2+40;i++) {
    if(await page.evaluate(s=>document.activeElement.matches(s),selector)) return;
    await page.keyboard.press(reverse?'Shift+Tab':'Tab');
  }
  throw new Error(`Cannot reach ${selector} with ${reverse?'Shift+Tab':'Tab'}`);
}
async function transform(page) {
  return page.locator('#canvas').evaluate(el=>{
    const m=new DOMMatrix(getComputedStyle(el).transform); return {scale:m.a,x:m.e,y:m.f};
  });
}
async function focusedNodeVisible(page) {
  await expect.poll(()=>page.evaluate(()=>{
    const el=document.activeElement;
    if(!el.matches('.node'))return false;
    const n=el.getBoundingClientRect(),w=document.querySelector('#wrap').getBoundingClientRect();
    const a=document.querySelector('#node-actions').getBoundingClientRect(),c=document.querySelector('#view-controls').getBoundingClientRect();
    return n.left>=w.left && n.right<=w.right && n.top>=w.top && n.bottom<=Math.min(w.bottom,a.top,c.top);
  })).toBe(true);
  await expect(page.locator('.node:focus')).toHaveCSS('outline-style','solid');
}
async function screenshot(page,testInfo,name,locator=page) {
  const file=testInfo.outputPath(name+'.png');
  await locator.screenshot({path:file});
  await testInfo.attach(name,{path:file,contentType:'image/png'});
}
module.exports={test,expect,docs,stats,paths,modules,root,openNav,openPanorama,moduleFilter,tabTo,transform,focusedNodeVisible,screenshot};
