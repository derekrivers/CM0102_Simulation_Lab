// Real Chromium/IndexedDB recovery and failure controls. Never logs private state.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve('../..'),out=path.resolve('test-output');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const hash=v=>createHash('sha256').update(v).digest('hex');
const encoded=v=>JSON.stringify(canonical(v));
const equal=(a,b,label)=>assert.equal(hash(encoded(a)),hash(encoded(b)),label);
const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native execution');return JSON.parse(p.stdout);};
const command=(state,id,plan)=>state.schema_version===5?{action:['human_command','registry_option_command','effective_plan_command'][plan%3],command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.registry.human.club_id,[plan%3===1?'value':'slot']:plan%2}}:state.schema_version===4?{action:plan%2?'registry_option_command':'human_command',command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.human.club_id,[plan%2?'value':'slot']:plan%2}}:state.schema_version===3?{action:'human_command',command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.club_id,slot:plan%2}}:({action:'command',command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.clubs[0].id,plan_id:plan}});
let injection='';
const assets=new Set(['index.html','app.js','worker.js','storage.js','style.css','cm_management.wasm']);
const server=http.createServer((req,res)=>{const file=req.url==='/'?'index.html':req.url.slice(1);if(!assets.has(file)){res.writeHead(404).end();return;}
 res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type',file.endsWith('.wasm')?'application/wasm':file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html');
 const data=fs.readFileSync(path.join('dist',file));res.end(file==='storage.js'?data.toString()+injection:data);
});
const request=(page,op)=>page.evaluate(op=>window.managementDurableRequest(op),op);
async function ready(page,url){await page.goto(url);await page.locator('button').filter({hasText:/^Apply (plan|slot)$/}).waitFor();}
async function editHead(page,change){return page.evaluate(async change=>{
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('cm-management-checkpoints-v1',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 await new Promise((resolve,reject)=>{const tx=db.transaction('checkpoints','readwrite'),store=tx.objectStore('checkpoints'),read=store.get('active');
  read.onsuccess=()=>{const head=read.result;if(change==='corrupt')head.current.save='corrupt';
   if(change==='identity')head.current.identity.revision+=1;
   if(change==='malformed-head')head.version=0;
   if(change==='both-invalid'){head.current.save='corrupt-current';head.previous.save='corrupt-previous';}
   if(change==='unsupported'){head.current.save='{}';head.current.save_sha256='44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a';}
   store.put(head,'active');};tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error);
 });db.close();
 },change);}
async function head(page){return page.evaluate(async()=>{
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('cm-management-checkpoints-v1',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 const result=await new Promise((resolve,reject)=>{const tx=db.transaction('checkpoints'),r=tx.objectStore('checkpoints').get('active');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});db.close();return result;
});}

(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url='http://127.0.0.1:'+server.address().port;
 fs.mkdirSync(out,{recursive:true});const userData=fs.mkdtempSync(path.join(out,'storage-profile-'));
 const launch=()=>chromium.launchPersistentContext(userData,{headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 let context=await launch();const results=[],controls=[];
 try{
  let page=context.pages()[0];await ready(page,url);
  const fixtures=[null,fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-managers-v1.json'),'utf8')];
  if(process.env.REFERENCE_FIXTURE)fixtures.push(fs.readFileSync(process.env.REFERENCE_FIXTURE,'utf8'));
  fixtures.push(fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-human-registry.json'),'utf8'));
  if(process.env.HUMAN_REFERENCE_FIXTURE)fixtures.push(fs.readFileSync(process.env.HUMAN_REFERENCE_FIXTURE,'utf8'));
  if(process.env.FRESH_HUMAN_REFERENCE_FIXTURE)fixtures.push(fs.readFileSync(process.env.FRESH_HUMAN_REFERENCE_FIXTURE,'utf8'));
  const registryFixtures=[fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-registry-producer.json'),'utf8')];
  if(process.env.REGISTRY_REFERENCE_FIXTURE)registryFixtures.push(fs.readFileSync(process.env.REGISTRY_REFERENCE_FIXTURE,'utf8'));
  if(process.env.FRESH_REGISTRY_REFERENCE_FIXTURE)registryFixtures.push(fs.readFileSync(process.env.FRESH_REGISTRY_REFERENCE_FIXTURE,'utf8'));
  fixtures.push(...registryFixtures);
  if(process.env.STORAGE_INVALID_HEADS_ONLY==='1'){
   const invalid_heads=await require('./check-invalid-storage.cjs')({page,context,url,request,ready,head,editHead,command,native,equal,fixture:registryFixtures.at(-1)});
   const receipt={schema_version:1,browser_version:context.browser().version(),invalid_heads,
    wasm_sha256:hash(fs.readFileSync('dist/cm_management.wasm')),scope:'invalid persistent heads only; full storage acceptance not run'};
   fs.writeFileSync(path.join(out,'invalid-head-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
   console.log(JSON.stringify(receipt));return;
  }
  const effectiveFixtures=[fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-effective-plan.json'),'utf8')];
  if(process.env.EFFECTIVE_REFERENCE_FIXTURE)effectiveFixtures.push(fs.readFileSync(process.env.EFFECTIVE_REFERENCE_FIXTURE,'utf8'));
  if(process.env.FRESH_EFFECTIVE_REFERENCE_FIXTURE)effectiveFixtures.push(fs.readFileSync(process.env.FRESH_EFFECTIVE_REFERENCE_FIXTURE,'utf8'));
  fixtures.push(...effectiveFixtures);
  for(const fixture of fixtures){
   const initial=fixture?{action:JSON.parse(fixture).schema_version===3&&JSON.parse(fixture).registry?'import_effective_reference':JSON.parse(fixture).schema_version===2&&JSON.parse(fixture).human?'import_registry_reference':JSON.parse(fixture).registry_row_sha256?'import_human_reference':'import_reference',fixture}:{action:'reset'};
   const first=await request(page,initial);assert.equal(first.ok,true);
   const a=command(first.state,'durable-a',1),one=await request(page,a),b=command(one.state,'durable-b',2),two=await request(page,b);
   assert.equal(two.durability.status,'saved');equal(two.state,native([initial,a,b]).at(-1).state,'native state before reopen');
   const saved=(await request(page,{action:'save'})).result;
   await context.close();context=await launch();page=context.pages()[0];await ready(page,url);
   const recovered=await request(page,{action:'state'});equal(recovered.state,two.state,'close/reopen exact state/events/records');
   assert.equal((await request(page,{action:'save'})).result,saved,'exact Rust save survives reopen');
   const duplicate=await request(page,b);equal(duplicate.state,two.state,'dedup after reopen');
   const duplicateInitial=await request(page,a);equal(duplicateInitial.state,two.state,'earlier mixed command dedup after reopen');
   const c=command(two.state,'durable-continuation',0),continued=await request(page,c);
   equal(continued.state,native([initial,a,b,b,c]).at(-1).state,'native deterministic continuation');
   results.push({profile:two.state.profile,fixture_sha256:two.state.fixture_sha256,save_sha256:hash(saved),recovered_state_sha256:hash(encoded(recovered.state)),native_continuation_equal:true});
  }
  controls.push('persistent browser process close/reopen; exact native state/events/dedup/save/continuation for every current profile');

  // Reject imported saves atomically, without replacing storage.
  const before=await head(page),state=(await request(page,{action:'state'})).state;
  const bad=await request(page,{action:'load',save:'unsupported'});assert.equal(bad.ok,false);equal(bad.state,state,'bad import memory');equal(await head(page),before,'bad import storage');
  controls.push('invalid import preserves memory and committed bytes');

  const freshControls=process.env.FRESH_HUMAN_REFERENCE_FIXTURE&&process.env.HUMAN_REFERENCE_FIXTURE?await require('./check-fresh-storage.cjs')({page,context,url,request,ready,head,editHead,command,native,equal,setInjection:value=>{injection=value;}}):null;

  const registryControls=await require('./check-registry-storage.cjs')({page,context,url,request,ready,head,editHead,native,equal,setInjection:value=>{injection=value;},fixtures:registryFixtures});

  const effectiveControls=await require('./check-effective-storage.cjs')({page,context,url,request,ready,head,editHead,native,equal,setInjection:value=>{injection=value;},fixtures:effectiveFixtures});

  const invalidHeadControls=await require('./check-invalid-storage.cjs')({page,context,url,request,ready,head,editHead,command,native,equal,fixture:registryFixtures.at(-1)});

  for(const change of ['corrupt','unsupported','identity']){
   const reset=await request(page,{action:'reset'}),a=command(reset.state,'fallback-a-'+change,1),one=await request(page,a);
   await request(page,command(one.state,'fallback-b-'+change,2));await editHead(page,change);
   await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
   const recovered=await request(page,{action:'state'});assert.equal(recovered.durability.status,'fallback');equal(recovered.state,one.state,change+' fallback');
   assert.match(await page.getByTestId('durability').textContent(),/previous valid checkpoint/);
  }
  controls.push('corrupt save, unsupported Rust save and mismatched identity recover previous valid checkpoint');

  // A real IndexedDB transaction is explicitly aborted after its put request.
  const reset=await request(page,{action:'reset'}),stable=await request(page,command(reset.state,'stable',1));
  const stableHead=await head(page);
  injection="\nconst originalPut=IDBObjectStore.prototype.put; IDBObjectStore.prototype.put=function(...args){const r=originalPut.apply(this,args);this.transaction.abort();return r;};";
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  const aborted=await request(page,command(stable.state,'abort',2));assert.equal(aborted.ok,true);assert.equal(aborted.durability.status,'failed');
  assert.equal(aborted.durability.durable.revision,stable.state.revision);equal(await head(page),stableHead,'aborted publication retained head');
  injection='';await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();equal((await request(page,{action:'state'})).state,stable.state,'unsaved command did not survive');
  controls.push('actual transaction abort preserves previous head and unsaved command is absent after reload');

  // Deterministic API fault; actual disk exhaustion is deliberately not induced.
  // Chromium's CDP quota override reported quota=1 but still admitted IDB writes;
  // that attempted control is retained as a limitation, never labeled a pass.
  injection="\nIDBObjectStore.prototype.put=function(){throw new DOMException('quota','QuotaExceededError');};";
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  const quota=await request(page,command(stable.state,'quota',3));assert.equal(quota.ok,true);assert.equal(quota.durability.status,'failed');equal(await head(page),stableHead,'quota preserves head');
  injection='';
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  controls.push('injected QuotaExceededError aborts real transaction and preserves committed head');

  // Security denial injection at IndexedDB entry, with real browser worker/UI.
  injection="\nopenDatabase=()=>Promise.reject(new DOMException('denied','SecurityError'));";
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  const denied=await request(page,{action:'reset'});assert.equal(denied.durability.status,'failed');equal(await head(page),stableHead,'denial preserves head');
  assert.match(await page.getByTestId('durability').textContent(),/Browser save failed/);
  injection='';await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  controls.push('injected storage SecurityError is visible and preserves real IndexedDB head');

  // Kill a worker while a real write transaction is held open after put.
  await page.addInitScript(()=>{const Original=window.Worker;window.Worker=class extends Original{constructor(...args){super(...args);this.addEventListener('message',event=>{if(event.data.storageTest)window.storageTest=event.data.storageTest;});}};});
  injection="\nconst realPut=IDBObjectStore.prototype.put; IDBObjectStore.prototype.put=function(...args){const r=realPut.apply(this,args);const store=this;function keepAlive(){const q=store.get('active');q.onsuccess=keepAlive;}keepAlive();self.postMessage({storageTest:'uncommitted'});return r;};";
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  await page.evaluate(state=>{window.interrupted=window.managementDurableRequest({action:'command',command:{session_id:state.session_id,command_id:'interrupted',expected_revision:state.revision,club_id:state.clubs[0].id,plan_id:4}});},stable.state);
  await page.waitForFunction(()=>window.storageTest==='uncommitted');
  injection='';await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  equal((await request(page,{action:'state'})).state,stable.state,'interrupted write rolls back');equal(await head(page),stableHead,'interrupted transaction head');
  controls.push('worker termination during actual uncommitted IndexedDB write rolls back');

  // Delayed old publication must finish before imported/reset sessions, by queue order.
  injection="\nconst realPublish=publishCheckpoint;let delayOnce=true;publishCheckpoint=async(...args)=>{if(delayOnce){delayOnce=false;await new Promise(resolve=>setTimeout(resolve,150));}return realPublish(...args);};";
  await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
  const ops=[command(stable.state,'race-command',3),{action:'import_reference',fixture:fixtures[1]},{action:'reset'}];
  const race=await page.evaluate(ops=>Promise.all(ops.map(op=>window.managementDurableRequest(op))),ops);
  assert.equal(race.every(r=>r.durability.status==='saved'),true);equal((await head(page)).current.identity,race.at(-1).durability.durable,'reset fences older/profile writes');
  injection='';await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();equal((await request(page,{action:'state'})).state,race.at(-1).state,'race recovery');
  controls.push('delayed command/import/reset publication is serialized across host sessions and profiles');

  // Both tabs recover the same token; only one may publish a replacement.
  const other=await context.newPage();await ready(other,url);
  const base=(await request(page,{action:'state'})).state,latest=await request(page,command(base,'tab-winner',1));
  const stale=await request(other,command(base,'tab-stale',2));assert.equal(stale.ok,true);assert.equal(stale.durability.status,'failed');assert.match(stale.durability.error,/conflict/);
  equal((await head(page)).current.identity,latest.durability.durable,'stale tab cannot overwrite');await other.close();
  controls.push('concurrent stale tab cannot replace a newer committed checkpoint');

  // Initial storage failure cannot grant a later retry another tab's token.
  injection="\nconst originalOpen=openDatabase;let denyFirstOpen=true;openDatabase=()=>{if(denyFirstOpen){denyFirstOpen=false;return Promise.reject(new DOMException('denied','SecurityError'));}return originalOpen();};";
  const failedTab=await context.newPage();await ready(failedTab,url);injection='';
  const failedState=(await request(failedTab,{action:'state'})).state;
  assert.equal(failedState.revision,0);
  await request(page,{action:'import_reference',fixture:fixtures[1]});
  const newerHead=await head(page);
  const retry=await request(failedTab,command(failedState,'retry-after-first-open-failure',1));
  assert.equal(retry.ok,true);assert.equal(retry.durability.status,'failed');assert.match(retry.durability.error,/conflict/);
  equal(await head(page),newerHead,'failed recovery retry cannot adopt another session token');
  await failedTab.close();
  controls.push('transient initial-open failure followed by another tab session change cannot rebind a publication retry');

  const receipt={schema_version:1,browser_version:context.browser().version(),profiles:results,controls,limitations:['SecurityError and QuotaExceededError are injected at IndexedDB API boundaries; abort/corruption/interruption and retained checkpoints use actual browser storage','Chromium CDP quota override reported quota=1 but admitted tested IndexedDB writes; actual disk exhaustion was not qualified','origin-local browser transaction guarantees; no physical-media/power-loss claim','raw private saves and profile remain only in ignored local test output'],wasm_sha256:hash(fs.readFileSync('dist/cm_management.wasm'))};
  receipt.fresh_admission=freshControls;
  receipt.registry_producer=registryControls;
  receipt.invalid_heads=invalidHeadControls;
  receipt.effective_lookup=effectiveControls;
  fs.writeFileSync(path.join(out,'storage-receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
 }finally{await context.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
