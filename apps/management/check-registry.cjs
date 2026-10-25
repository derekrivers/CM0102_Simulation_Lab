// Actual Rust WASM/native producer corpus and neutral React controls.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const encoded=v=>JSON.stringify(canonical(v)),hash=v=>createHash('sha256').update(v).digest('hex');
const equal=(a,b,label)=>assert.equal(hash(encoded(a)),hash(encoded(b)),label);
const importFixture=fixture=>({action:'import_registry_reference',fixture});
const command=(state,id,revision,kind,value)=>({action:kind==='RegistryOptionTwoSet'?'registry_option_command':'human_command',
 command:{session_id:state.session_id,command_id:id,expected_revision:revision,club_id:state.fixture.human.club_id,
 [kind==='RegistryOptionTwoSet'?'value':'slot']:value}});
module.exports=async function checkRegistry(page,root,out,fixtureText){
 const fixture=JSON.parse(fixtureText),human=fixture.human;
 const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native registry runner failed');return JSON.parse(p.stdout);};
 const retainedOracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/human-registry-producer-oracle-v1.json')));
 const freshOracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/fresh-human-registry-producer-oracle-v1.json')));
 const oracle=human.source_capture_sha256===freshOracle.capture.source_capture_sha256?freshOracle:retainedOracle;
 assert.equal(oracle.producer_cases.length,7);assert.equal(oracle.mixed_cases.length,10);
 const initial=native([importFixture(fixtureText)])[0];assert.equal(initial.ok,true,'registry fixture admission');
 assert.equal(initial.state.schema_version,4);assert.equal(initial.state.fixture.guard_9a01,fixture.guard_9a01);
 const accepted=[...oracle.producer_cases.map(c=>({kind:'RegistryOptionTwoSet',value:c.value,case:c})),
  ...oracle.mixed_cases.map(c=>({kind:c.kind,value:c.kind==='RegistryOptionTwoSet'?c.value:c.slot,case:c}))];
 const prefix=[importFixture(fixtureText),...accepted.map((c,i)=>command(initial.state,'registry-oracle-'+i,i,c.kind,c.value))];
 const observations=native(prefix);
 for(let i=0;i<accepted.length;i++){
  const {kind,case:c}=accepted[i],r=observations[i+1];assert.equal(r.ok,true,'original registry case');
  assert.equal(r.result.kind,kind);assert.deepEqual(r.result.ordered_writes,c.ordered_writes.map(write=>({...write,registry_index:human.registry_index})),'complete original ordered write sequence');
  assert.equal(r.state.fixture.guard_9a01,fixture.guard_9a01,'immutable observed DWORD');
  for(let j=0;j<c.ordered_writes.length;j++){
   for(const field of ['registry_offset','width','value'])assert.equal(r.result.ordered_writes[j][field],c.ordered_writes[j][field],'original ordered effect');
   assert.equal(r.result.ordered_writes[j].registry_index,human.registry_index);
  }
  if(i<oracle.producer_cases.length){
   assert.equal(r.result.old_value,c.previous_value);assert.equal(r.result.new_value,c.new_value);
   assert.equal(r.state.option_two,c.new_value);assert.equal(r.state.selected_slot,human.selected_slot);
  }else{
   assert.equal(r.state.option_two,c.option_two);assert.equal(r.state.selected_slot,c.selected_slot);
   if(kind==='RegistryOptionTwoSet'){assert.equal(r.result.old_value,c.previous_value);assert.equal(r.result.new_value,c.option_two);}
   else{assert.equal(r.result.old_slot,c.previous_slot);assert.equal(r.result.new_slot,c.selected_slot);}
  }
 }
 const revision=accepted.length,state=observations.at(-1).state;
 const wrongClub=command(state,'wrong-club',revision,'RegistryOptionTwoSet',0);wrongClub.command.club_id=human.club_count;
 const wrongSession=command(state,'wrong-session',revision,'RegistryOptionTwoSet',0);wrongSession.command.session_id='unsupported';
 const changedFixture=structuredClone(fixture);changedFixture.guard_9a01=1-fixture.guard_9a01;
 const rejects=[command(state,'negative-value',revision,'RegistryOptionTwoSet',-1),command(state,'upper-value',revision,'RegistryOptionTwoSet',2),
  command(state,'wide-value',revision,'RegistryOptionTwoSet',65536),command(state,'stale-value',0,'RegistryOptionTwoSet',0),
  command(state,'negative-slot',revision,'HumanSlotSelected',-1),command(state,'upper-slot',revision,'HumanSlotSelected',2),
  wrongClub,wrongSession,command(state,'registry-oracle-0',0,'HumanSlotSelected',0),importFixture(JSON.stringify(changedFixture)),
  {action:'command',command:{session_id:state.session_id,command_id:'wrong-capability',expected_revision:revision,club_id:human.club_id,plan_id:0}}];
 prefix.push(...rejects,{action:'save'});
 const first=native(prefix),saved=first.at(-1).result;assert.equal(JSON.parse(saved).schema_version,4);
 for(let i=prefix.length-rejects.length-1;i<prefix.length-1;i++){assert.equal(first[i].ok,false);equal(first[i].state,state,'rejection atomicity');}
 assert.equal(first[prefix.length-rejects.length-1+8].error,'command-id-conflict','cross-command ID conflict');
 const option=command(state,'mixed-continuation-option',revision,'RegistryOptionTwoSet',1);
 const slot=command(state,'mixed-continuation-slot',revision+1,'HumanSlotSelected',1);
 const operations=[...prefix,option,slot,{action:'load',save:saved},prefix[1],option,option,slot,slot,
  command(state,'mixed-continuation-option',revision,'HumanSlotSelected',0),{action:'load',save:'corrupt'}];
 const legacy=fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/legacy-plan-v1.json'),'utf8');
 const ordinary=fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-managers-v1.json'),'utf8');
 const v2=native([{action:'import_reference',fixture:ordinary},{action:'save'}]).at(-1).result;
 const v3=native([{action:'import_human_reference',fixture:JSON.stringify(human)},{action:'save'}]).at(-1).result;
 const oldExports=[];
 for(const oldSave of [legacy,v2,v3]){operations.push({action:'load',save:oldSave},command(state,'older-profile-producer',0,'RegistryOptionTwoSet',1),{action:'save'});oldExports.push([operations.length-1,oldSave]);}
 operations.push({action:'load',save:saved},{action:'save'});
 const roundtripIndex=operations.length-1;
 for(const mutate of [
  p=>{p.option_two=1-p.option_two;},p=>{p.fixture.guard_9a01=1-p.fixture.guard_9a01;},
  p=>{p.fixture.human.registry_row_sha256='0'.repeat(64);},
  p=>{p.events[0].ordered_writes[0].registry_offset=0x9b24;},
  p=>{p.records[0].result.ordered_writes[0].width=2;},p=>{p.records.reverse();}
 ]){
  const envelope=JSON.parse(saved),payload=JSON.parse(envelope.payload);mutate(payload);
  envelope.payload=JSON.stringify(payload);envelope.payload_bytes=Buffer.byteLength(envelope.payload);
  envelope.payload_sha256=hash(envelope.payload);operations.push({action:'load',save:JSON.stringify(envelope)});
 }
 const expected=native(operations);
 for(let i=1;i<expected.length;i++)if(!expected[i].ok)equal(expected[i].state,expected[i-1].state,'full rejection state');
 for(const [index,oldSave] of oldExports)assert.equal(expected[index].result,oldSave,'v1-v3 byte roundtrip');
 assert.equal(expected[roundtripIndex].result,saved,'v4 byte roundtrip');
 for(const r of expected.slice(roundtripIndex+1)){assert.equal(r.ok,false,'checksum-repaired tamper rejected');equal(r.state,state,'tamper atomicity');}
 const actual=await page.evaluate(async ops=>{const results=[];for(const op of ops)results.push(await window.managementRequest(op));return results;},operations);
 equal(actual,expected,'registry full native/browser equality');
 await page.reload();await page.locator('button').filter({hasText:/^Apply (plan|slot)$/}).waitFor();
 await page.getByLabel('Import club fixture',{exact:true}).setInputFiles({name:'registry-fixture.json',mimeType:'application/json',buffer:Buffer.from(fixtureText)});
 await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
 assert.equal(await page.getByTestId('registry-guard').textContent(),String(fixture.guard_9a01));
 await page.getByLabel('Choose registry option 2',{exact:true}).selectOption('1');
 await page.getByRole('button',{name:'Apply registry option 2',exact:true}).click();
 await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
 assert.equal(await page.getByTestId('selected-option-two').textContent(),'1');
 await page.getByLabel('Choose a research slot',{exact:true}).selectOption('1');await page.getByRole('button',{name:'Apply slot',exact:true}).click();
 await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
 const uiState=await page.evaluate(()=>window.managementRequest({action:'state'}));
 assert.equal(uiState.state.selected_slot,1);assert.equal(uiState.state.option_two,1);
 assert.equal(uiState.state.fixture.guard_9a01,fixture.guard_9a01);
 assert.match(await page.getByTestId('durability').textContent(),/Saved in this browser: revision 2/);
 const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Export state',exact:true}).click();
 const output=path.join(out,human.origin+'-'+hash(encoded(fixture)).slice(0,12)+'-registry-slice-v4.json');await(await downloadEvent).saveAs(output);
 await page.getByLabel('Choose registry option 2',{exact:true}).selectOption('0');await page.getByRole('button',{name:'Apply registry option 2',exact:true}).click();
 await page.getByRole('status').filter({hasText:'revision 3'}).waitFor();
 await page.getByLabel('Import state',{exact:true}).setInputFiles(output);await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
 await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
 equal((await page.evaluate(()=>window.managementRequest({action:'state'}))).state,uiState.state,'v4 UI persisted state/effects/records');
 await page.getByLabel('Import club fixture',{exact:true}).setInputFiles({name:'changed-fixture.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(changedFixture))});
 await page.getByRole('status').filter({hasText:'Rejected:'}).waitFor();
 equal((await page.evaluate(()=>window.managementRequest({action:'state'}))).state,uiState.state,'changed wrapper rejected atomically');
 await page.getByRole('button',{name:'New fictional session',exact:true}).click();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Apply registry option 2',exact:true}).count(),0);
 return {origin:human.origin,fixture_sha256:hash(encoded(fixture)),operations:operations.length,
  original_producer_cases:oracle.producer_cases.length,original_mixed_cases:oracle.mixed_cases.length,
  native_browser_equal:true,canonical_sha256:hash(encoded(actual)),
  controls:['producer/mixed original ordered writes and immutable DWORD','invalid value/slot/club/session/revision/capability atomicity',
   'cross-command ID conflict','v1-v4 byte roundtrips','checksum-repaired v4 tamper rejection',
   'capability-gated neutral UI, v4 import/export/reload and invalid fixture atomicity']};
};
