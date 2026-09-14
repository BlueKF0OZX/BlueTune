const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
(async()=>{
  const browser = await chromium.launch({headless:true, ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:8091');
    await page.getByRole('button',{name:'Run demo checkup'}).waitFor();
    assert.match(await page.locator('#mode-note').innerText(),/DEMO/);
    await page.locator('#measure').click();
    await page.getByRole('heading',{name:'No overload detected in this sample'}).waitFor();
    await page.locator('#save').click();
    await page.locator('#scenario').selectOption('clipping');
    assert.equal(await page.locator('#export').isDisabled(),true);
    await page.locator('#measure').click();
    await page.getByRole('heading',{name:'Clipping appeared in this sample'}).waitFor();
    assert.match(await page.locator('#comparison').innerText(),/0 → 18/);
    const downloadEvent=page.waitForEvent('download'); await page.locator('#export').click();
    const download=await downloadEvent;
    const artifact=path.join(__dirname,'../artifacts'); fs.mkdirSync(artifact,{recursive:true});
    await download.saveAs(path.join(artifact,'checkup-test.json'));
    const exported=JSON.parse(fs.readFileSync(path.join(artifact,'checkup-test.json')));
    assert.equal(exported.current.source,'demo'); assert.equal(exported.baseline.source,'demo');
    await page.locator('#scenario').selectOption('paste');
    await page.locator('#stats').fill('RxAudioStats: Pk -8.0 Avg Pwr -21 Min -60 Max -15 dBFS ClipCnt 0');
    await page.locator('#measure').click();
    await page.getByRole('heading',{name:'Confirm your speech sample'}).waitFor();
    assert.match(await page.locator('#comparison').innerText(),/different sources/);
    await page.locator('#speech').check();
    await page.getByRole('heading',{name:'No overload detected in this sample'}).waitFor();
    await page.locator('#stats').fill('RxAudioStats: bad'); await page.locator('#measure').click();
    await page.locator('#error').waitFor();
    assert.equal(await page.locator('#save').isDisabled(),true);
    await page.locator('#scenario').selectOption('quiet'); await page.locator('#measure').click();
    await page.getByRole('heading',{name:'Very little input was measured'}).waitFor();
    await page.locator('#scenario').selectOption('balanced'); await page.locator('#measure').click();
    await page.getByRole('heading',{name:'No overload detected in this sample'}).waitFor();
    await page.locator('#clear').click();
    await page.screenshot({path:path.join(artifact,'bluetune-desktop.png'),fullPage:true});
    for (const width of [390,320,768]) {
      await page.setViewportSize({width,height:844});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`Overflow at ${width}px`);
      if(width===390) await page.screenshot({path:path.join(artifact,'bluetune-mobile.png'),fullPage:true});
    }
    // Simulated live endpoint tests exercise the UI without any Asterisk access.
    const realStatus=await (await page.request.get('http://127.0.0.1:8091/api/status')).json();
    await page.route('**/api/status',route=>route.fulfill({json:{mode:'live',device:'1999',token:realStatus.token,version:'test'}}));
    await page.route('**/api/sample',route=>route.fulfill({status:400,json:{error:'The active SimpleUSB device does not match this session.'}}));
    await page.reload(); await page.getByRole('button',{name:'Measure for 10 seconds'}).waitFor();
    await page.locator('#measure').click(); await page.locator('#error').waitFor();
    assert.equal(await page.locator('#save').isDisabled(),true);
    await page.unroute('**/api/sample');
    await page.route('**/api/sample',route=>route.fulfill({json:{sample:{peak:-8,average:-21,minimum:-60,maximum:-15,clips:0},device:'1999',collected_at:Date.now()/1000}}));
    await page.locator('#measure').click(); await page.locator('#stop').click();
    await page.waitForFunction(()=>document.querySelector('#progress').textContent.includes('canceled'));
    assert.equal(await page.locator('#save').isDisabled(),true);
    await page.locator('#speech').check();
    await page.locator('#measure').click();
    await page.getByRole('heading',{name:'No overload detected in this sample'}).waitFor({timeout:20000});
    assert.ok(Number(await page.locator('#count').innerText())>=5);
    assert.match(await page.locator('#sample-badge').innerText(),/LIVE/);
    assert.deepEqual(errors,[]);
    console.log('Browser checks passed: examples, speech confirmation, comparison isolation, export, malformed input, 3 responsive widths, simulated live success, error and cancellation.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exit(1)});
