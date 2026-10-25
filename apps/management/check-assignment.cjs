// Deferred acceptance: run only after independent LL1 acceptance releases execution.
// No fixture output is a golden; native/WASM equality and original evidence are separate.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn,spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../..'),out=path.resolve(__dirname,'test-output');
const hash=v=>createHash('sha256').update(v).digest('hex');
const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:64*1024*1024});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout);};
const command=(state,id,member)=>({action:member===undefined?'assignment_readback_command':'assignment_command',command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.club_id,slot:0,...(member===undefined?{}:{staff_id:member})}});
const imported=fixture=>({action:'import_assignment_reference',fixture});
const request=(page,op,durable=false)=>page.evaluate(({op,durable})=>durable?window.managementDurableRequest(op):window.managementRequest(op),{op,durable});
async function preview(fixture){
 const child=spawn(process.execPath,[path.join(__dirname,'preview.cjs')],{env:{...process.env,MANAGEMENT_PREVIEW_PORT:'0',ASSIGNMENT_REFERENCE_FIXTURE:fixture},stdio:['ignore','pipe','pipe']});
 const url=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>{child.kill();reject(new Error('preview timeout'));},10000);child.once('exit',()=>{clearTimeout(timer);reject(new Error('preview exited'));});child.stdout.on('data',chunk=>{output+=chunk;const m=output.match(/http:\/\/127\.0\.0\.1:\d+/);if(m){clearTimeout(timer);resolve(m[0]);}});});
 return {url,close:()=>new Promise(resolve=>{child.once('exit',resolve);child.kill();})};
}
async function head(page){return page.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('cm-management-checkpoints-v1',1);r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result,t=db.transaction('checkpoints','readonly'),get=t.objectStore('checkpoints').get('active');get.onsuccess=()=>resolve(get.result);t.oncomplete=()=>db.close();};}));}
async function corruptCurrent(page){await page.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('cm-management-checkpoints-v1',1);r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result,t=db.transaction('checkpoints','readwrite'),s=t.objectStore('checkpoints'),get=s.get('active');get.onsuccess=()=>{const value=get.result;value.current.save+='corrupt';s.put(value,'active');};t.oncomplete=()=>{db.close();resolve();};t.onabort=()=>{db.close();reject(t.error);};};}));}
const ready=async(page,url)=>{await page.goto(url);await page.getByRole('status').filter({hasText:'State ready'}).waitFor();};
(async()=>{
 assert.ok(process.env.ASSIGNMENT_REFERENCE_FIXTURE,'Exact admitted private fixture path required');
 fs.mkdirSync(out,{recursive:true});const runDirectory=fs.mkdtempSync(path.join(out,'assignment-acceptance-'));fs.chmodSync(runDirectory,0o700);const results=[],started=Date.now();
 for(const [label,file] of [['synthetic',path.join(root,'crates/cm-management/tests/fixtures/synthetic-assignment.json')],['retained',process.env.ASSIGNMENT_REFERENCE_FIXTURE]]){
  const fixture=fs.readFileSync(file,'utf8'),initial=native([imported(fixture)])[0];assert.equal(initial.ok,true);
  const host=await preview(file),profile=fs.mkdtempSync(path.join(runDirectory,label+'-profile-'));
  const options={headless:true,executablePath:process.env.CHROMIUM_PATH};let context;
  try{
   context=await chromium.launchPersistentContext(profile,options);let page=await context.newPage();await ready(page,host.url);
   await page.getByRole('button',{name:'Load two-member reference',exact:true}).click();await page.getByRole('button',{name:'Read back slot zero',exact:true}).waitFor();
   assert.match(await page.getByTestId('squad-boundary').textContent(),/incomplete|Complete squad/);
   assert.match(await page.getByTestId('data-origin').textContent(),label==='synthetic'?/Fictional/:/Captured reference/);
   assert.deepEqual((await request(page,{action:'state'})).state,initial.state);
   // Same corpus through actual WASM and native: every response, immutable field,
   // mapping entry, event, rejection and save byte is compared without masking.
   const ops=[imported(fixture)];let state=initial.state;
   const sequence=[undefined,state.fixture.members[0],undefined,state.fixture.members[0],undefined,state.fixture.members[1],undefined];
   for(const [i,member] of sequence.entries()){const op=command(state,'corpus-'+i,member);ops.push(op);state=native(ops).at(-1).state;}
   const checkpoint=native([...ops,{action:'save'}]).at(-1).result;
   for(const suffix of [0,1]){ops.push({action:'load',save:checkpoint});state=native(ops).at(-1).state;for(const member of [state.fixture.members[0],undefined]){ops.push(command(state,'suffix-'+(member===undefined?'read':'assign'),member));state=native(ops).at(-1).state;}}
   const valid=command(state,'host-negative',state.fixture.members[0]);
   for(const slot of [-1,1,20,256])ops.push({...valid,command:{...valid.command,slot}});
   ops.push({...valid,command:{...valid.command,staff_id:2147483648}});
   ops.push({...valid,command:{...valid.command,session_id:'wrong'}});
   ops.push({...valid,command:{...valid.command,expected_revision:0}});
   ops.push({...valid,command:{...valid.command,staff_id:-1}});
   ops.push(valid,valid,{...valid,command:{...valid.command,staff_id:state.fixture.members[1]}},{action:'save'});
   const expected=native(ops),actual=[];for(const op of ops)actual.push(await request(page,op));assert.deepEqual(actual,expected,'complete native/WASM corpus');
   if(label==='retained')fs.writeFileSync(path.join(runDirectory,'assignment-retained-corpus.json'),JSON.stringify({fixture_sha256:initial.state.fixture_sha256,operations:ops,responses:actual}),{mode:0o600,flag:'wx'});
   // Start a clean persisted profile for real UI interactions and reopen.
   await request(page,imported(fixture),true);await page.reload();await page.getByRole('button',{name:'Read back slot zero',exact:true}).waitFor();
   const first=state.fixture.members[0],second=state.fixture.members[1];
   await page.getByRole('button',{name:'Assign staff ID '+first,exact:true}).click();await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
   await page.getByRole('button',{name:'Read back slot zero',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
   const saved=await request(page,{action:'save'}),accepted=await request(page,{action:'state'});assert.equal((await head(page)).current.identity.revision,2);
   assert.deepEqual(accepted,native([imported(fixture),...accepted.state.records.map(r=>r.command),{action:'state'}]).at(-1));
   await context.close();context=await chromium.launchPersistentContext(profile,options);page=await context.newPage();await ready(page,host.url);assert.deepEqual((await request(page,{action:'state'})).state,accepted.state,'actual persistent process reopen');
   await page.getByRole('button',{name:'Assign staff ID '+second,exact:true}).click();await page.getByRole('status').filter({hasText:'revision 3'}).waitFor();
   const continued=await request(page,{action:'state'});assert.deepEqual(continued,native([{action:'load',save:saved.result},continued.state.records.at(-1).command,{action:'state'}]).at(-1));
   assert.match(await page.getByTestId('assignment-readback').textContent(),/revision 2/,'readback remains historical');
   const exported=path.join(profile,'export.json'),download=page.waitForEvent('download');await page.getByRole('button',{name:'Export state',exact:true}).click();await(await download).saveAs(exported);
   assert.equal(fs.readFileSync(exported,'utf8'),(await request(page,{action:'save'})).result);
   await page.getByRole('button',{name:'Assign staff ID '+first,exact:true}).click();await page.getByRole('status').filter({hasText:'revision 4'}).waitFor();
   await page.getByLabel('Import state',{exact:true}).setInputFiles(exported);await page.getByRole('status').filter({hasText:'revision 3'}).waitFor();assert.deepEqual((await request(page,{action:'state'})).state,continued.state,'discriminating import');
   // Corrupt current -> previous valid; preserve exact full state on recovery.
   await request(page,command(continued.state,'backup-read'),true);const backup=await request(page,{action:'state'});
   await request(page,command(backup.state,'current-assign',first),true);await corruptCurrent(page);await page.reload();await page.getByTestId('durability').filter({hasText:'previous valid checkpoint'}).waitFor();assert.deepEqual((await request(page,{action:'state'})).state,backup.state);
   // A second tab that recovered the same profile cannot overwrite a newer head.
   const stale=await context.newPage();await ready(stale,host.url);const winner=await request(page,command(backup.state,'winner',second),true),winnerHead=await head(page);
   const loser=await request(stale,command(backup.state,'stale',first),true);assert.equal(loser.ok,true);assert.equal(loser.durability.status,'failed');assert.match(loser.durability.error,/conflict/);assert.deepEqual(await head(page),winnerHead);await stale.close();
   // Actual aborted IndexedDB transaction keeps accepted in-memory action visible.
   await page.reload();await page.getByRole('button',{name:'Read back slot zero',exact:true}).waitFor();
   const engineWorker=page.workers().find(worker=>new URL(worker.url()).pathname==='/worker.js');assert.ok(engineWorker,'actual engine worker available');
   await engineWorker.evaluate(()=>{self.assignmentAbortCount=0;const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){const result=put.apply(this,args);self.assignmentAbortCount++;this.transaction.abort();return result;};});
   await page.getByRole('button',{name:'Read back slot zero',exact:true}).click();await page.getByTestId('durability').filter({hasText:'Browser save failed'}).waitFor();
   assert.ok(await engineWorker.evaluate(()=>self.assignmentAbortCount)>0,'abort hook executed in publishing worker realm');
   const unsaved=await request(page,{action:'state'});assert.equal(unsaved.state.revision,winner.state.revision+1);assert.deepEqual(await head(page),winnerHead);
   assert.deepEqual(unsaved.state,native([{action:'load',save:winnerHead.current.save},unsaved.state.records.at(-1).command]).at(-1).state);
   results.push({label,fixture_sha256:initial.state.fixture_sha256,operations:ops.length,native_wasm_equal:true,process_reopen:true,continuation:true,export_import:true,corrupt_fallback:true,stale_writer_fenced:true,actual_abort:true});
  }finally{if(context)await context.close();await host.close();}
 }
 const receipt={schema_version:1,kind:'bounded-assignment-acceptance-v1',artifact_directory:runDirectory,elapsed_seconds:(Date.now()-started)/1000,wasm_sha256:hash(fs.readFileSync(path.join(__dirname,'dist/cm_management.wasm'))),cases:results,scope:'Two admitted records and slot zero only. Original effect comparator and unchanged legacy suites remain separate required checks.'};
 fs.writeFileSync(path.join(runDirectory,'assignment-acceptance-receipt.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o600,flag:'wx'});console.log(JSON.stringify(receipt));
})().catch(error=>{console.error(error);process.exitCode=1;});
