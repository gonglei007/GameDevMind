'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.resolve(__dirname, '../../nav/node-activation.js'), 'utf8');
const create = vm.runInNewContext(source + '\ncreateNodeActivation');
function fixture() {
  let now = 0, serial = 0;
  const timers = new Map();
  const toggles = [], opens = [];
  const activation = create(node => toggles.push(node), node => opens.push(node), 500,
    (callback, delay) => { const id = ++serial; timers.set(id, {callback, at: now + delay}); return id; },
    id => timers.delete(id));
  return {activation, toggles, opens, advance(ms) {
    now += ms;
    for (const [id, timer] of timers) {
      if (timer.at <= now) { timers.delete(id); timer.callback(); }
    }
  }};
}
const parent = {children: [{}]};
const leaf = {children: []};

test('A delayed parent single-click toggles once; leaf single-click does nothing', () => {
  const f = fixture();
  f.activation.click(parent);
  f.advance(499);
  assert.equal(f.toggles.length, 0);
  f.advance(1);
  assert.deepEqual(f.toggles, [parent]);
  f.advance(1000);
  f.activation.click(leaf);
  f.advance(1000);
  assert.deepEqual(f.toggles, [parent]);
  assert.equal(f.opens.length, 0);
});

test('Two clicks followed by a double-click open without collapsing or redrawing', () => {
  const f = fixture();
  f.activation.click(parent);
  f.advance(400);
  f.activation.click(parent);
  f.activation.doubleClick(parent);
  f.advance(1000);
  assert.deepEqual(f.opens, [parent]);
  assert.equal(f.toggles.length, 0);
  f.activation.doubleClick(leaf);
  assert.deepEqual(f.opens, [parent, leaf]);
});

test('Redraw cancellation or a different target prevents a stale toggle', () => {
  const f = fixture();
  f.activation.click(parent);
  f.activation.cancel();
  f.advance(1000);
  assert.equal(f.toggles.length, 0);
  f.activation.click(parent);
  f.activation.click(leaf);
  f.advance(1000);
  assert.equal(f.toggles.length, 0);
});
