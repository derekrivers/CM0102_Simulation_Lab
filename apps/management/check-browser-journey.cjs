// Additive on-demand setup journey; existing canonical/storage suites stay unchanged.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn,spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve('../..'),out=path.resolve('test-output');fs.mkdirSync(out,{recursive:true});
const hash=v=>createHash('sha256').update(v).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const equal=(a,b,label)=>assert.deepEqual(canonical(a),canonical(b),label);
const native=ops=>{const r=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(r.status,0,'native corpus failed');return JSON.parse(r.stdout);};
async function preview(fixture){
 const child=spawn(process.execPath,['preview.cjs'],{env:{...process.env,MANAGEMENT_PREVIEW_PORT:'0',EFFECTIVE_REFERENCE_FIXTURE:fixture||''},stdio:['ignore','pipe','pipe']});
 const url=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>{child.kill();reject(new Error('preview startup timeout'));},10000);child.once('exit',()=>{clearTimeout(timer);reject(new Error('preview exited'));});child.stdout.on('data',chunk=>{text+=chunk;const match=text.match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timer);resolve(match[0]);}});});
 return {url,close:()=>new Promise(resolve=>{child.once('exit',resolve);child.kill();})};
}
(async()=>{
 const started=Date.now(),results=[];
 for(const key of ['EFFECTIVE_REFERENCE_FIXTURE','FRESH_EFFECTIVE_REFERENCE_FIXTURE'])assert.ok(process.env[key],key+' required for complete journey acceptance');
 const fixtures=[['synthetic',path.join(root,'crates/cm-management/tests/fixtures/synthetic-effective-plan.json')]];
 for(const [label,key] of [['retained','EFFECTIVE_REFERENCE_FIXTURE'],['fresh','FRESH_EFFECTIVE_REFERENCE_FIXTURE']])if(process.env[key])fixtures.push([label,process.env[key]]);
 const invalid=path.join(out,'journey-invalid-fixture.json');fs.writeFileSync(invalid,'{}');
 const oversized=path.join(out,'journey-oversized-fixture.json');fs.writeFileSync(oversized,' '.repeat(65537));
 // Missing, relative-path and Rust-rejected fixture routes preserve the exact active world.
 for(const [label,fixture] of [['missing',null],['relative','relative.json'],['invalid',invalid],['oversized',oversized]]){
  const host=await preview(fixture),browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
  try{const page=await browser.newPage();await page.goto(host.url);await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();const before=await page.evaluate(()=>window.managementRequest({action:'state'}));
   await page.getByRole('button',{name:'Load connected human reference',exact:true}).click();await page.getByRole('status').filter({hasText:label==='invalid'?'Rejected:':'No qualified connected'}).waitFor();
   equal((await page.evaluate(()=>window.managementRequest({action:'state'}))).state,before.state,label+' setup is atomic');
   assert.equal((await page.request.get(host.url+'/effective-reference-fixture.json')).status(),label==='invalid'?200:404);
   for(const route of ['/../package.json','/%2e%2e/package.json','/effective-reference-fixture.json?path=/etc/passwd'])assert.equal((await page.request.get(host.url+route)).status(),404);
   results.push({case:label,atomic:true});
  }finally{await browser.close();await host.close();}
 }
 for(const [label,fixture] of fixtures){
  const fixtureText=fs.readFileSync(fixture,'utf8'),host=await preview(fixture),profile=fs.mkdtempSync(path.join(out,'journey-'+label+'-'));
  const options={headless:true,executablePath:process.env.CHROMIUM_PATH};let browser;
  try{
   browser=await chromium.launchPersistentContext(profile,options);let page=await browser.newPage();await page.goto(host.url);await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
   await page.getByRole('button',{name:'Load connected human reference',exact:true}).click();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
   assert.match(await page.getByTestId('squad-boundary').textContent(),/No qualified squad records/);
   assert.match(await page.getByTestId('data-origin').textContent(),label==='synthetic'?/Fictional data/:/Captured reference/);
   const query=()=>page.evaluate(()=>window.managementRequest({action:'state'}));const initial=await query();
   equal(initial.state,native([{action:'import_effective_reference',fixture:fixtureText}])[0].state,'setup full native/WASM state');
   await page.getByLabel('Choose lookup slot',{exact:true}).selectOption('1');equal((await query()).state,initial.state,'control selection is pure');
   await page.getByRole('button',{name:'Look up effective plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
   const accepted=await query(),ops=[{action:'import_effective_reference',fixture:fixtureText},...accepted.state.records.map(r=>r.command),{action:'state'},{action:'save'}];
   const expected=native(ops);equal(accepted,expected.at(-2),'explicit UI command full response native equality');
   const save=await page.evaluate(()=>window.managementRequest({action:'save'}));equal(save,expected.at(-1),'exact native/WASM save');
   await page.getByRole('button',{name:'Save in browser',exact:true}).click();await page.getByTestId('durability').filter({hasText:'Saved in this browser: revision 1'}).waitFor();
   await browser.close();browser=await chromium.launchPersistentContext(profile,options);page=await browser.newPage();await page.goto(host.url);await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();equal((await query()).state,accepted.state,'actual process close/reopen');
   await page.getByLabel('Choose a research slot',{exact:true}).selectOption('1');await page.getByRole('button',{name:'Apply slot',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
   const continued=await query();equal(continued,native([{action:'load',save:save.result},continued.state.records.at(-1).command,{action:'state'}]).at(-1),'reopened full continuation native equality');
   assert.match(await page.getByTestId('effective-result').textContent(),/Last explicit lookup · revision 1/);
   const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export state',exact:true}).click();const exported=path.join(profile,'export.json');await(await download).saveAs(exported);
   assert.equal(fs.readFileSync(exported,'utf8'),native([{action:'load',save:save.result},continued.state.records.at(-1).command,{action:'save'}]).at(-1).result,'export exact bytes');
   await page.getByLabel('Choose a research slot',{exact:true}).selectOption('0');await page.getByRole('button',{name:'Apply slot',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 3'}).waitFor();
   assert.equal((await query()).state.revision,3,'state differs before restore');
   await page.getByLabel('Import state',{exact:true}).setInputFiles(exported);await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();equal((await query()).state,continued.state,'export/import preserves world');
   results.push({case:label,fixture_sha256:hash(JSON.stringify(canonical(JSON.parse(fixtureText)))),native_wasm_equal:true,process_reopen:true,continued_revision:continued.state.revision});
  }finally{if(browser)await browser.close();await host.close();}
 }
 const receipt={schema_version:1,retained_and_fresh_executed:true,elapsed_seconds:(Date.now()-started)/1000,wasm_sha256:hash(fs.readFileSync('dist/cm_management.wasm')),cases:results,scope:'Existing v5 setup/explicit lookup/save/reopen/continuation; no qualified squad or lineup action. Existing corruption/abort/fencing acceptance remains separate.'};
 fs.writeFileSync(path.join(out,'browser-journey-receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
})().catch(error=>{console.error(error);process.exitCode=1;});
