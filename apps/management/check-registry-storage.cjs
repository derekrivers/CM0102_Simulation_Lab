// Real IndexedDB producer failure recovery and same-profile fixture fencing.
const fs=require('node:fs'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
const load=fixture=>({action:'import_registry_reference',fixture});
const command=(state,id,kind,value)=>({action:kind==='option'?'registry_option_command':'human_command',
 command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.human.club_id,[kind==='option'?'value':'slot']:value}});
module.exports=async function registryStorage({page,context,url,request,ready,head,editHead,native,equal,setInjection,fixtures}){
 const profiles=[],controls=[];
 for(let index=0;index<fixtures.length;index++){
  const fixture=fixtures[index],first=await request(page,load(fixture));assert.equal(first.ok,true);
  const a=command(first.state,'registry-backup-option','option',1),one=await request(page,a);
  const b=command(one.state,'registry-backup-slot','slot',1),backup=await request(page,b);
  const saved=(await request(page,{action:'save'})).result;
  const duplicateOption=await request(page,a),duplicateSlot=await request(page,b);
  equal(duplicateOption.state,backup.state,'producer retry after mixed command');equal(duplicateSlot.state,backup.state,'slot retry');
  const conflict=command(first.state,'registry-backup-option','slot',0);
  const rejected=await request(page,conflict);assert.equal(rejected.error,'command-id-conflict');equal(rejected.state,backup.state,'cross-command conflict');
  const c=command(backup.state,'registry-current-option','option',0);await request(page,c);
  await editHead(page,'corrupt');const corrupt=await head(page);
  await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
  const recovered=await request(page,{action:'state'});assert.equal(recovered.durability.status,'fallback');
  equal(recovered.state,backup.state,'v4 corrupt current falls back');equal(recovered.state,native([load(fixture),a,b]).at(-1).state,'mixed native recovery');
  assert.match(await page.getByTestId('durability').textContent(),/previous valid checkpoint/);
  setInjection("\nconst registryPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){const r=registryPut.apply(this,args);this.transaction.abort();return r;};");
  await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
  await page.getByLabel('Choose registry option 2',{exact:true}).selectOption('0');
  await page.getByRole('button',{name:'Apply registry option 2',exact:true}).click();
  await page.getByTestId('durability').filter({hasText:'Browser save failed'}).waitFor();
  const unsaved=await request(page,{action:'state'});assert.equal(unsaved.state.revision,backup.state.revision+1);
  assert.equal(unsaved.state.option_two,0);assert.equal(unsaved.state.selected_slot,backup.state.selected_slot);
  equal(await head(page),corrupt,'actual abort preserves entire v4 head');
  assert.equal(unsaved.durability.durable.revision,backup.state.revision);
  const last=unsaved.state.records.at(-1).command;
  // The exact command accepted by Rust is replayed; no TypeScript state model.
  equal(unsaved.state,native([{action:'load',save:saved},last]).at(-1).state,'unsaved v4 producer equals native');
  setInjection('');await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
  equal((await request(page,{action:'state'})).state,backup.state,'unsaved producer absent after reload');
  profiles.push({fixture_sha256:backup.state.fixture_sha256,profile:backup.state.profile,
   recovered_state_sha256:digest(recovered.state),mixed_dedup_equal:true,actual_abort_preserved:true});
 }
 controls.push('each v4 fixture: mixed command deduplication and cross-command conflict, corrupt-current fallback, visible actual transaction abort and native unsaved state');
 let sameProfile=null;
 if(process.env.REGISTRY_REFERENCE_FIXTURE&&process.env.FRESH_REGISTRY_REFERENCE_FIXTURE){
  const retainedFixture=fs.readFileSync(process.env.REGISTRY_REFERENCE_FIXTURE,'utf8');
  const freshFixture=fs.readFileSync(process.env.FRESH_REGISTRY_REFERENCE_FIXTURE,'utf8');
  const retained=await request(page,load(retainedFixture)),retainedHead=await head(page);
  setInjection("\nconst registryPublish=publishCheckpoint;let delayRegistry=true;publishCheckpoint=async(...args)=>{if(delayRegistry){delayRegistry=false;await new Promise(resolve=>setTimeout(resolve,150));}return registryPublish(...args);};");
  await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
  const delayed=command(retained.state,'retained-option-before-fresh','option',1);
  const operations=[delayed,load(freshFixture)];
  const race=await page.evaluate(ops=>Promise.all(ops.map(op=>window.managementDurableRequest(op))),operations);
  assert.equal(race.every(r=>r.ok&&r.durability.status==='saved'),true);
  equal(race.map(r=>r.state),native([load(retainedFixture),...operations]).slice(1).map(r=>r.state),'ordered retained/fresh v4 publication');
  const freshHead=await head(page);assert.equal(freshHead.current.identity.fixture_sha256,digest(JSON.parse(freshFixture)));
  assert.notEqual(freshHead.current.host_session,retainedHead.current.host_session);
  setInjection('');await page.reload();await page.getByRole('button',{name:'Apply registry option 2',exact:true}).waitFor();
  equal((await request(page,{action:'state'})).state,race[1].state,'same-profile producer import survives reload');
  const staleTab=await context.newPage();await ready(staleTab,url);
  const winner=await request(page,load(retainedFixture)),winnerHead=await head(page);
  assert.equal(winner.state.profile,race[1].state.profile);assert.equal(winner.state.session_id,race[1].state.session_id);
  assert.notEqual(winnerHead.current.identity.fixture_sha256,freshHead.current.identity.fixture_sha256);
  assert.notEqual(winnerHead.current.host_session,freshHead.current.host_session);
  const stale=await request(staleTab,command(race[1].state,'fresh-stale-option','option',1));
  assert.equal(stale.ok,true);assert.equal(stale.durability.status,'failed');assert.match(stale.durability.error,/conflict/);
  equal(await head(page),winnerHead,'same-profile stale producer cannot overwrite retained import');
  await staleTab.close();
  sameProfile={retained_fixture_sha256:winner.state.fixture_sha256,fresh_fixture_sha256:race[1].state.fixture_sha256,
   delayed_import_equal:true,stale_producer_fenced:true};
  controls.push('retained/fresh v4 shared profile/session: delayed producer/import serialization and stale producer tab fencing');
 }
 return {profiles,controls,same_profile_fencing:sameProfile};
};
