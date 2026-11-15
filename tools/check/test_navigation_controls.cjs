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
function fixture(file) {
  class Element {
    constructor() {
      this.style = {}; this.dataset = {}; this.listeners = {}; this.children = [];
      this.value = ''; this.attributes = {}; this.className = '';
      const classes = new Set();
      this.classList = {add: x => classes.add(x), remove: x => classes.delete(x),
        toggle: (x, on) => on ? classes.add(x) : classes.delete(x)};
    }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    setAttribute(name, value) { this.attributes[name] = value; }
    appendChild(el) { this.children.push(el); el.parent = this; }
    remove() { this.parent.children = this.parent.children.filter(el => el !== this); }
    getBoundingClientRect() { return {left:0, top:160, width:390, height:684}; }
    querySelectorAll(selector) {
      if (selector !== '.edge-line') return [];
      return [...(this.innerHTML || '').matchAll(/data-parent="([^"]*)" data-child="([^"]*)"/g)]
        .map(match => ({dataset:{parent:match[1],child:match[2]},style:{}}));
    }
  }
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const timers = new Map(); let serial = 0;
  const context = vm.createContext({
    document: {readyState:'loading', getElementById:get, createElement:()=>new Element(),
      querySelectorAll:()=>[], querySelector:()=>null},
    window: {addEventListener() {}, open() {}}, location:{hostname:'localhost'},
    setTimeout(fn) { const id=++serial; timers.set(id,fn); return id; },
    clearTimeout: id=>timers.delete(id), requestAnimationFrame:fn=>fn(),
  });
  vm.runInContext(read('nav/content-data.js'), context);
  vm.runInContext(read('nav/node-activation.js'), context);
  const script = read(file).match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(script, context);
  return {get, run:code=>vm.runInContext(code,context), flush() {
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
