const {defineConfig} = require('@playwright/test');
const path = require('node:path');
const artifacts = path.resolve(__dirname, '../../../output/playwright-regression');
const port = Number(process.env.BROWSER_TEST_PORT || 4173);

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  workers: 1,
  retries: 0,
  timeout: 45000,
  globalTimeout: 10 * 60 * 1000,
  expect: {timeout: 10000},
  outputDir: path.join(artifacts, 'results'),
  reporter: [
    ['list'],
    ['html', {outputFolder:path.join(artifacts, 'report'), open:'never'}],
    ['json', {outputFile:path.join(artifacts, 'results.json')}],
  ],
  use: {
    browserName:'chromium',
    channel:process.env.PLAYWRIGHT_CHANNEL || undefined,
    baseURL:`http://127.0.0.1:${port}`,
    viewport:{width:1440, height:1000},
    actionTimeout:10000,
    navigationTimeout:45000,
    trace:'retain-on-failure',
    screenshot:'only-on-failure',
    video:'retain-on-failure',
  },
  webServer: {
    command:'node server.cjs',
    url:`http://127.0.0.1:${port}/healthz`,
    reuseExistingServer:false,
    timeout:15000,
  },
  projects: [
    {name:'desktop', testMatch:/(navigation|panorama|keyboard)\.spec\.cjs/},
    {name:'mobile', testMatch:/mobile\.spec\.cjs/,
      use:{viewport:{width:390,height:844}, isMobile:true, hasTouch:true, deviceScaleFactor:1}},
    {name:'github-readme', testMatch:/readme\.spec\.cjs/},
  ],
});
