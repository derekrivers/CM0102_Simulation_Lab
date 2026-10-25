// Native/actual WASM connected lookup corpus plus explicit React workflow.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const encoded=v=>JSON.stringify(canonical(v)),hash=v=>createHash('sha256').update(v).digest('hex');
const equal=(a,b,label)=>assert.equal(hash(encoded(a)),hash(encoded(b)),label);
const load=fixture=>({action:'import_effective_reference',fixture});
const command=(state,id,revision,kind,value)=>({action:{lookup:'effective_plan_command',select:'human_command',option:'registry_option_command'}[kind],
 command:{session_id:state.session_id,command_id:id,expected_revision:revision,club_id:state.fixture.registry.human.club_id,[kind==='option'?'value':'slot']:value}});
module.exports=async function checkEffective(page,root,out,fixtureText){
 const fixture=JSON.parse(fixtureText),human=fixture.registry.human;
 const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native effective runner');return JSON.parse(p.stdout);};
 const fresh=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/pc-r7-fresh-effective-plan-v1.json')));
 const oracle=human.source_capture_sha256===fresh.capture.source_capture_sha256?fresh:JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/pc-r7-retained-effective-plan-v1.json')));
 const first=native([load(fixtureText)])[0];assert.equal(first.ok,true,'effective fixture admitted');assert.equal(first.state.schema_version,5);
 const operations=[load(fixtureText),...oracle.cases.map((c,i)=>command(first.state,'effective-oracle-'+i,i,c.kind,c.value))];
 const original=native(operations);
 for(let i=0;i<oracle.cases.length;i++){
  const c=oracle.cases[i],r=original[i+1];assert.equal(r.ok,true);equal(r.state.fixture,fixture,'immutable fixture');
  assert.equal(r.state.selected_slot,c.selected_slot);assert.equal(r.state.option_two,c.option_two);
  equal(r.result.ordered_writes,c.ordered_writes.map(w=>({...w,registry_index:human.registry_index})),'original ordered writes');
  if(c.kind==='lookup'){
   assert.equal(r.result.kind,'EffectivePlanLookedUp');assert.equal(r.result.branch,c.branch);
   const location={...c.location};if(location.kind==='human_registry')location.registry_index=human.registry_index;
   equal(r.result.location,location,'tagged original return');assert.equal(r.result.requested_slot,c.value);
   assert.equal(r.result.old_slot,c.previous_slot);assert.equal(r.result.new_slot,c.selected_slot);
   assert.equal(r.result.option_two,c.option_two);
  }
 }
 const state=original.at(-1).state,revision=state.revision;
 const wrongClub=command(state,'bad-club',revision,'lookup',0);wrongClub.command.club_id=human.club_count;
 const wrongSession=command(state,'bad-session',revision,'lookup',0);wrongSession.command.session_id='unsupported';
 const changed=structuredClone(fixture);changed.ordinary.first_bank_sha256='0'.repeat(64);
 const rejected=[command(state,'negative',revision,'lookup',-1),command(state,'upper',revision,'lookup',2),command(state,'wide',revision,'lookup',65536),
  command(state,'stale',0,'lookup',0),wrongClub,wrongSession,command(state,'effective-oracle-0',0,'option',0),load(JSON.stringify(changed)),
  {action:'command',command:{session_id:state.session_id,command_id:'wrong-capability',expected_revision:revision,club_id:human.club_id,plan_id:0}}];
 const rejectStart=operations.length;operations.push(...rejected,{action:'save'});
 const prefix=native(operations),saved=prefix.at(-1).result;assert.equal(JSON.parse(saved).schema_version,5);
 for(const r of prefix.slice(rejectStart,-1)){assert.equal(r.ok,false);equal(r.state,state,'invalid operation atomicity');}
 const continuation=[command(state,'continued-option',revision,'option',1),command(state,'continued-lookup',revision+1,'lookup',1),command(state,'continued-select',revision+2,'select',0)];
 const continuationStart=operations.length;
 operations.push(...continuation,{action:'load',save:saved},operations[1],...continuation,continuation[0],continuation[1],continuation[2],
  command(state,'continued-lookup',revision+1,'select',1),{action:'load',save:'corrupt'},{action:'load',save:saved},{action:'save'});
 const roundtrip=operations.length-1;
 for(const mutate of [p=>{p.selected_slot=1-p.selected_slot;},p=>{p.fixture.ordinary.selected_plan=1;},p=>{p.records.reverse();},
  p=>{const event=p.events.find(e=>e.kind==='EffectivePlanLookedUp');event.location.kind='unsupported';},
  p=>{const event=p.events.find(e=>e.kind==='EffectivePlanLookedUp');event.branch='unsupported';}]){
  const envelope=JSON.parse(saved),payload=JSON.parse(envelope.payload);mutate(payload);
  envelope.payload=JSON.stringify(payload);envelope.payload_bytes=Buffer.byteLength(envelope.payload);envelope.payload_sha256=hash(envelope.payload);
  operations.push({action:'load',save:JSON.stringify(envelope)});
 }
 const oldSaves=[fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/legacy-plan-v1.json'),'utf8'),
  native([{action:'import_reference',fixture:fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/synthetic-managers-v1.json'),'utf8')},{action:'save'}]).at(-1).result,
  native([{action:'import_human_reference',fixture:JSON.stringify(human)},{action:'save'}]).at(-1).result,
  native([{action:'import_registry_reference',fixture:JSON.stringify(fixture.registry)},{action:'save'}]).at(-1).result];
 const oldChecks=[];
 for(const save of oldSaves){operations.push({action:'load',save},command(state,'old-profile-lookup',0,'lookup',0),{action:'save'});oldChecks.push([operations.length-1,save]);}
 const expected=native(operations);
 for(let i=0;i<3;i++)equal(expected[continuationStart+i].state,expected[continuationStart+5+i].state,'mixed checkpoint continuation');
 for(let i=8;i<=10;i++)equal(expected[continuationStart+i].state,expected[continuationStart+7].state,'mixed retry returns accepted history');
 for(let i=1;i<expected.length;i++)if(!expected[i].ok)equal(expected[i].state,expected[i-1].state,'rejected operation preserves full world');
 assert.equal(expected[roundtrip].result,saved,'v5 exact byte roundtrip');
 for(const r of expected.slice(roundtrip+1,roundtrip+6))assert.equal(r.ok,false,'checksum-repaired history tamper rejected');
 for(const [i,save] of oldChecks){assert.equal(expected[i-1].ok,false,'old profile lacks lookup');assert.equal(expected[i].result,save,'v1-v4 exact byte roundtrip');}
 const actual=await page.evaluate(async ops=>{const results=[];for(const op of ops)results.push(await window.managementRequest(op));return results;},operations);
 equal(actual,expected,'full connected native/WASM corpus');
 await page.reload();await page.locator('button').filter({hasText:/^Apply (plan|slot)$/}).waitFor();
 await page.getByLabel('Import club fixture',{exact:true}).setInputFiles({name:'effective-fixture.json',mimeType:'application/json',buffer:Buffer.from(fixtureText)});
 await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
 assert.match(await page.getByTestId('effective-result').textContent(),/No explicit lookup/);
 const query=()=>page.evaluate(()=>window.managementRequest({action:'state'}));
 const imported=await query();assert.equal(imported.state.revision,0);
 await page.getByLabel('Choose lookup slot',{exact:true}).selectOption('1');equal((await query()).state,imported.state,'render/control selection stays pure');
 await page.getByRole('button',{name:'Look up effective plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
 async function checkResult(){const r=await query(),event=r.state.events.filter(e=>e.kind==='EffectivePlanLookedUp').at(-1);assert.equal(await page.getByTestId('effective-branch').textContent(),event.branch);const text=await page.getByTestId('effective-location').textContent();assert.match(text,new RegExp(event.location.kind));assert.match(text,new RegExp('byte offset '+event.location.byte_offset));return r;}
 const lookupOne=await checkResult();equal((await query()).state,lookupOne.state,'state inspection does not invoke lookup');
 await page.getByLabel('Choose a research slot',{exact:true}).selectOption('1');await page.getByRole('button',{name:'Apply slot',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
 assert.match(await page.getByTestId('effective-result').textContent(),/Last explicit lookup · revision 1/);
 await page.getByLabel('Choose registry option 2',{exact:true}).selectOption('1');await page.getByRole('button',{name:'Apply registry option 2',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 3'}).waitFor();
 await page.getByLabel('Choose lookup slot',{exact:true}).selectOption('0');
 for(const revision of [4,5]){await page.getByRole('button',{name:'Look up effective plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision '+revision}).waitFor();await checkResult();}
 const ui=await query();assert.equal(ui.state.selected_slot,0);assert.equal(ui.state.option_two,1);
 const uiOps=ui.state.records.map(r=>r.command);equal(ui.state,native([load(fixtureText),...uiOps]).at(-1).state,'UI connected command native equality');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export state',exact:true}).click();
 const output=path.join(out,hash(encoded(fixture)).slice(0,12)+'-effective-slice-v5.json');await(await download).saveAs(output);
 await page.getByLabel('Choose registry option 2',{exact:true}).selectOption('0');await page.getByRole('button',{name:'Apply registry option 2',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 6'}).waitFor();
 await page.getByRole('button',{name:'Look up effective plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 7'}).waitFor();await checkResult();
 await page.getByLabel('Import state',{exact:true}).setInputFiles(output);await page.getByRole('status').filter({hasText:'revision 5'}).waitFor();
 await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();equal((await checkResult()).state,ui.state,'v5 durable UI save/load/reload');
 await page.getByLabel('Import club fixture',{exact:true}).setInputFiles({name:'invalid-effective.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(changed))});await page.getByRole('status').filter({hasText:'Rejected:'}).waitFor();equal((await query()).state,ui.state,'unsupported fixture atomicity');
 await page.getByRole('button',{name:'New fictional session',exact:true}).click();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Look up effective plan',exact:true}).count(),0);
 return {origin:human.origin,fixture_sha256:hash(encoded(fixture)),operations:operations.length,original_connected_cases:oracle.cases.length,native_browser_equal:true,canonical_sha256:hash(encoded(actual)),
  controls:['complete original ordered writes and tagged branch/location','invalid commands/imports/replays atomic','mixed three-command retry history and v1-v5 exact roundtrips','explicit lookup UI and pure render/query','historical result label, export/import/reload and capability removal']};
};
