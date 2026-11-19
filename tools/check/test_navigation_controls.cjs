'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

// Execute the actual page scripts with a small DOM adapter. These state/gesture
// checks complement Playwright's real layout, hit testing and mobile gestures.
function fixture(file, {deferFrames=false}={}) {
  const document = {readyState:'loading', activeElement:null};
  class Element {
    constructor() {
      this.style = {}; this.dataset = {}; this.listeners = {}; this.children = [];
      this.value = ''; this.attributes = {}; this.className = '';
      this.tabIndex = -1;
      const classes = new Set();
      this.classList = {add: x => classes.add(x), remove: x => classes.delete(x),
        toggle: (x, on) => on ? classes.add(x) : classes.delete(x)};
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    setAttribute(name, value) { this.attributes[name] = value; }
    getAttribute(name) { return this.attributes[name]; }
    matches(selector) { return selector === ':focus-visible'; }
    contains(el) { return el === this || this.children.some(child=>child.contains(el)); }
    focus() {
      if (document.activeElement === this) return;
      document.activeElement = this;
      this.listeners.focus?.();
    }
    set innerHTML(html) {
      if (this.contains(document.activeElement)) document.activeElement = document.body;
      this.html = html; this.children = [];
      for (const match of html.matchAll(/<button\b([^>]*)>/g)) {
        const el = new Element();
        for (const attr of match[1].matchAll(/([\w-]+)="([^"]*)"/g)) {
          el.attributes[attr[1]] = attr[2];
          if (attr[1] === 'data-focus-key') el.dataset.focusKey = attr[2];
          if (attr[1] === 'data-module') el.dataset.module = attr[2];
        }
        this.appendChild(el);
      }
    }
    get innerHTML() { return this.html || ''; }
    appendChild(el) { this.children.push(el); el.parent = this; }
    remove() {
      if (document.activeElement === this) document.activeElement = document.body;
      this.parent.children = this.parent.children.filter(el => el !== this);
    }
    getBoundingClientRect() { return {left:0, right:390, top:160, bottom:844, width:390, height:684}; }
    querySelectorAll(selector) {
      if (selector !== '.edge-line') return [];
      return [...(this.innerHTML || '').matchAll(/data-parent="([^"]*)" data-child="([^"]*)"/g)]
        .map(match => ({dataset:{parent:match[1],child:match[2]},style:{}}));
    }
  }
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  document.body = new Element(); document.activeElement = document.body;
  Object.assign(document, {getElementById:get, createElement:()=>new Element(),
    querySelectorAll:selector=>selector === '.tab' ? get('tabs').children : [],
    querySelector:selector=> {
      const key = selector.match(/^\[data-focus-key="([^"]+)"\]$/)?.[1];
      if (key) return [...get('tabs').children, ...get('paths').children].find(el=>el.dataset.focusKey===key);
      if (selector === '.tab[data-module="-1"]') return get('tabs').children.find(el=>el.dataset.module==='-1');
      return null;
    }});
  const windowListeners = {};
  const timers = new Map(), frames = []; let serial = 0;
  const context = vm.createContext({
    document,
    window: {addEventListener(name,fn) { windowListeners[name] = fn; }, open() {}}, location:{hostname:'localhost'},
    setTimeout(fn) { const id=++serial; timers.set(id,fn); return id; },
    clearTimeout: id=>timers.delete(id), requestAnimationFrame:fn=>deferFrames ? frames.push(fn) : fn(),
  });
  vm.runInContext(read('nav/content-data.js'), context);
  vm.runInContext(read('nav/node-activation.js'), context);
  const script = read(file).match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(script, context);
  return {get, document, windowListeners, run:code=>vm.runInContext(code,context), frame() {
    const pending = frames.splice(0); pending.forEach(fn=>fn());
  }, flush() {
    const pending = [...timers.values()]; timers.clear(); pending.forEach(fn=>fn());
  }};
}

test('Search trims whitespace; category, level, role and learning path filters intersect', () => {
  const f=fixture('nav/index.html');
  const count=()=>Number(f.get('stats').textContent.match(/显示 (\d+)/)[1]);
  f.get('search').value=' 网络 ';
  f.run('render()'); assert.equal(count(),6);
  f.get('search').value='c#';
  f.run('render()'); assert.equal(count(),1);
  f.get('search').value='';
  f.run("activeCat=3; activeLevels.add('中级'); activeRoles.add('服务端'); render()");
  assert.equal(count(), f.run("DOCS.filter(d=>d.c===3 && d.l===2 && d.r.split(',').includes('服务端')).length"));
  f.run("selectPath('b')");
  assert.equal(count(), f.run("DOCS.filter(d=>LEARNING_PATHS[1].paths.has(d.p) && d.l===2 && d.r.split(',').includes('服务端')).length"));
  f.run("activeLevels.clear(); activeRoles.clear(); selectPath('b')");
  assert.equal(count(),112);
});

test('Every module remains filtered after collapse/redraw and expands back; reset restores all', () => {
  const f=fixture('nav/panorama.html'); f.run('init()');
  for(let mod=0;mod<6;mod++) {
    f.run(`activeModule=${mod}; filterByModule(${mod}); nodeActivation.click(allRoots[${mod}])`);
    f.flush();
    assert.equal(f.run("[...nodeEls].filter(([,el])=>el.style.display!=='none').length"),1);
    assert.equal(f.run("[...nodeEls].filter(([n,el])=>el.style.display!=='none' && n.module!==activeModule).length"),0);
    f.run(`nodeActivation.click(allRoots[${mod}])`); f.flush();
    assert.equal(f.run("[...nodeEls].filter(([,el])=>el.style.display!=='none').length"),f.run(`DOCS.filter(d=>d.c===${mod+1}).length`));
    assert.ok(f.run('scale')>=1);
  }
  f.run('resetView()');
  assert.equal(f.run('activeModule'),-1);
  assert.equal(f.run('nodeEls.size'),112);
  assert.equal(f.get('node-actions').hidden,true);
});

test('Changing modules cancels a queued collapse', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); nodeActivation.click(allRoots[0]); activeModule=1; filterByModule(1)');
  f.flush(); assert.equal(f.run('allRoots[0].collapsed'),false);
});

test('A translated pinch preserves its initial world anchor; lifting one finger continues pan', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); scale=1; tx=10; ty=20');
  const emit=(type,points)=>f.get('wrap').listeners[type]({touches:points.map(([clientX,clientY])=>({clientX,clientY})),preventDefault(){}});
  emit('touchstart',[[100,300],[200,300]]);
  emit('touchmove',[[100,350],[300,350]]);
  assert.equal(f.run('scale'),2);
  assert.equal(f.run('tx'),-80);
  assert.equal(f.run('ty'),-50);
  emit('touchend',[[100,350]]);
  emit('touchmove',[[120,380]]);
  assert.equal(f.run('tx'),-60); assert.equal(f.run('ty'),-20);
  assert.equal(f.run('suppressNodeClick'),true);
  emit('touchcancel',[]); assert.equal(f.run('isDragging'),false);
});

test('Dragging a node does not collapse it; the next tap can activate it', () => {
  const f=fixture('nav/panorama.html'); f.run('init()');
  const emit=(type,x,y)=>f.get('wrap').listeners[type]({touches:[{clientX:x,clientY:y}],preventDefault(){}});
  emit('touchstart',100,300); emit('touchmove',150,350);
  f.run('onNodeClick(allRoots[0], {stopPropagation(){}})'); f.flush();
  assert.equal(f.run('allRoots[0].collapsed'),false);
  emit('touchstart',150,350);
  f.run('onNodeClick(allRoots[0], {stopPropagation(){}})'); f.flush();
  assert.equal(f.run('allRoots[0].collapsed'),true);
});

test('Zoom controls keep the viewport center anchored and respect scale limits', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); scale=1; tx=10; ty=20; zoomBy(1.2)');
  assert.equal(f.run('scale'),1.2);
  assert.equal(f.run('tx'),-27); assert.ok(Math.abs(f.run('ty')+44.4)<1e-9);
  f.run('zoomBy(1/1.2)');
  assert.ok(Math.abs(f.run('tx')-10)<1e-9); assert.ok(Math.abs(f.run('ty')-20)<1e-9);
  f.run('zoomBy(100)'); assert.equal(f.run('scale'),3);
  f.run('zoomBy(0.0001)'); assert.equal(f.run('scale'),0.1);
});

test('Deferred initial fit does not overwrite a module selection and button zoom', () => {
  const f=fixture('nav/panorama.html', {deferFrames:true});
  f.run('init(); activeModule=2; filterByModule(2)');
  f.frame();
  const before=f.run('JSON.stringify([scale,tx,ty])');
  f.run('zoomBy(1.2)');
  const zoomed=f.run('JSON.stringify([scale,tx,ty])');
  f.frame();
  assert.equal(f.run('JSON.stringify([scale,tx,ty])'),zoomed);
  f.run('zoomBy(1/1.2)');
  const actual=JSON.parse(f.run('JSON.stringify([scale,tx,ty])'));
  JSON.parse(before).forEach((value,i)=>assert.ok(Math.abs(actual[i]-value)<1e-9));
});

test('A pending resize fit does not overwrite subsequent zoom or pan', () => {
  for (const action of ['zoomBy(1.2)', 'tx+=40; ty+=30; updateTransform()']) {
    const f=fixture('nav/panorama.html'); f.run('init(); activeModule=2; filterByModule(2)');
    f.windowListeners.resize();
    f.run(action);
    const before=f.run('JSON.stringify([scale,tx,ty])');
    f.flush();
    assert.equal(f.run('JSON.stringify([scale,tx,ty])'),before);
  }
});

test('Initial and resize fits still run when the view has not been changed', () => {
  const f=fixture('nav/panorama.html', {deferFrames:true});
  f.run('init()');
  assert.equal(f.get('canvas').style.transform,undefined);
  f.frame(); f.frame();
  assert.match(f.get('canvas').style.transform,/scale\(/);
  f.run('scale=1; tx=10; ty=20');
  f.windowListeners.resize(); f.flush();
  assert.notEqual(f.run('tx'),10);
});

test('Category and learning-path redraws preserve focus; search input is not replaced', () => {
  const f=fixture('nav/index.html');
  f.document.querySelector('[data-focus-key="category-1"]').focus();
  f.run('activeCat=1; render()');
  assert.equal(f.document.activeElement.dataset.focusKey,'category-1');
  assert.equal(f.document.activeElement.getAttribute('aria-pressed'),'true');
  f.document.querySelector('[data-focus-key="path-b"]').focus();
  f.run("selectPath('b')");
  assert.equal(f.document.activeElement.dataset.focusKey,'path-b');
  assert.equal(f.document.activeElement.getAttribute('aria-pressed'),'true');
  f.run("selectPath('b')");
  assert.equal(f.document.activeElement.getAttribute('aria-pressed'),'false');
  f.get('search').focus(); f.get('search').value='网络'; f.run('render()');
  assert.equal(f.document.activeElement,f.get('search'));
});

test('Keyboard node activation bypasses touch suppression and redraws with focus retained', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); focusNode(allRoots[0]); suppressNodeClick=true');
  f.run('onNodeClick(allRoots[0], {detail:0, stopPropagation(){}})');
  assert.equal(f.run('allRoots[0].collapsed'),true);
  assert.equal(f.document.activeElement.dataset.name,'基础能力');
  assert.equal(f.document.activeElement.getAttribute('aria-expanded'),'false');
  f.run('onNodeClick(allRoots[0], {detail:0, stopPropagation(){}})');
  assert.equal(f.run('allRoots[0].collapsed'),false);
  assert.equal(f.document.activeElement.getAttribute('aria-expanded'),'true');
  assert.equal(f.run('[...nodeEls.values()].filter(el=>el.tabIndex===0).length'),1);
});

test('Arrow keys and Home/End navigate visible nodes, collapse and expand without losing focus', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); activeModule=0; filterByModule(0); focusNode(allRoots[0])');
  const press = key => f.run(`onNodeKeyDown([...nodeEls].find(([,el])=>el===document.activeElement)[0], {key:'${key}',preventDefault(){},stopPropagation(){}})`);
  press('ArrowRight'); assert.equal(f.document.activeElement.dataset.name,'编程语言');
  press('ArrowLeft'); assert.equal(f.document.activeElement.getAttribute('aria-expanded'),'false');
  press('ArrowRight'); assert.equal(f.document.activeElement.getAttribute('aria-expanded'),'true');
  press('ArrowRight'); assert.equal(f.document.activeElement.dataset.name,'编程语言基础概念');
  press('ArrowLeft'); assert.equal(f.document.activeElement.dataset.name,'编程语言');
  press('ArrowDown'); assert.equal(f.document.activeElement.dataset.name,'编程语言基础概念');
  press('ArrowUp'); assert.equal(f.document.activeElement.dataset.name,'编程语言');
  press('End'); assert.equal(f.document.activeElement.dataset.name,'计算机网络');
  press('Home'); assert.equal(f.document.activeElement.dataset.name,'基础能力');
  assert.equal(f.run('[...nodeEls].filter(([,el])=>el.tabIndex===0 && el.style.display!=="none").length'),1);
});

test('Global shortcuts ignore modifiers, composition, editable targets and handled events', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); scale=1');
  const target = {isContentEditable:false, closest:()=>null};
  const press=extra=> {
    let prevented=false;
    f.windowListeners.keydown({key:'-',target,preventDefault(){prevented=true;},...extra});
    return prevented;
  };
  for(const extra of [{ctrlKey:true},{metaKey:true},{altKey:true},{isComposing:true},{defaultPrevented:true},
    {target:{isContentEditable:true}}, {target:{closest:()=>({})}}]) {
    assert.equal(press(extra),false); assert.equal(f.run('scale'),1);
  }
  assert.equal(press({}),true); assert.equal(f.run('scale'),1/1.2);
  f.run('activeModule=0; allRoots[0].collapsed=true');
  for(const key of ['0','r','R']) {
    press({key}); assert.equal(f.run('activeModule'),-1); assert.equal(f.run('allRoots[0].collapsed'),false);
  }
});

test('Reset while an action link is focused returns focus to its node', () => {
  const f=fixture('nav/panorama.html'); f.run('init(); focusNode(allRoots[0])');
  f.get('node-actions').appendChild(f.get('selected-link')); f.get('selected-link').focus();
  f.run('resetView()');
  assert.equal(f.document.activeElement.dataset.name,'基础能力');
});
