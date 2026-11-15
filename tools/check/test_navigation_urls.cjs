'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {pathToFileURL, fileURLToPath} = require('node:url');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'nav/content-data.js'), 'utf8');
function navigation(hostname) {
  return vm.runInNewContext(source + '\n({contentHref, DOCS})', {location:{hostname}});
}

test('Pages documents open GitHub rendered files, preserving special filenames', () => {
  const {contentHref, DOCS} = navigation('gonglei007.github.io');
  for (const doc of DOCS) {
    const url = new URL(contentHref(doc.p));
    assert.equal(url.origin, 'https://github.com');
    assert.equal(decodeURIComponent(url.pathname), '/gonglei007/GameDevMind/blob/main/' + doc.p);
    assert.equal(url.hash, '');
    assert.equal(url.search, '');
  }
  const csharp = DOCS.find(doc => doc.t === 'C#语言');
  assert.ok(csharp);
  assert.ok(contentHref(csharp.p).includes('C%23'));
  const special = new URL(contentHref('mds/示例 #1 (新版).md'));
  assert.equal(decodeURIComponent(special.pathname), '/gonglei007/GameDevMind/blob/main/mds/示例 #1 (新版).md');
  assert.equal(special.hash, '');
});

test('Pages code collections open GitHub directory views', () => {
  const {contentHref, DOCS} = navigation('gonglei007.github.io');
  const examples = DOCS.filter(doc => doc.code);
  assert.ok(examples.length > 0);
  for (const doc of examples) {
    const url = new URL(contentHref(doc.code));
    assert.equal(url.origin, 'https://github.com');
    assert.equal(decodeURIComponent(url.pathname), '/gonglei007/GameDevMind/tree/main/' + doc.code);
    assert.equal(url.hash, '');
  }
});

test('Offline and local-server navigation keep relative file and directory destinations', () => {
  const base = pathToFileURL(path.join(root, 'nav/index.html'));
  for (const hostname of ['', 'localhost', '127.0.0.1']) {
    const {contentHref, DOCS} = navigation(hostname);
    for (const doc of DOCS) {
      for (const target of [doc.p, doc.code].filter(Boolean)) {
        const href = contentHref(target);
        assert.equal(new URL(href, 'http://localhost/nav/').origin, 'http://localhost');
        const url = new URL(href, base);
        assert.equal(url.protocol, 'file:');
        assert.equal(url.hash, '');
        assert.equal(path.resolve(fileURLToPath(url)), path.resolve(root, target));
        assert.ok(fs.existsSync(fileURLToPath(url)));
      }
    }
  }
});
