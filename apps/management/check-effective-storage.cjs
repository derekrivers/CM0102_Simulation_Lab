// Connected lookup publication, recovery and writer fencing in actual IndexedDB.
const assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
const load=fixture=>({action:'import_effective_reference',fixture});
const command=(state,id,kind,value)=>({action:{lookup:'effective_plan_command',select:'human_command',option:'registry_option_command'}[kind],
 command:{session_id:state.session_id,command_id:id,expected_revision:state.revision,club_id:state.fixture.registry.human.club_id,[kind==='option'?'value':'slot']:value}});
module.exports=async function effectiveStorage({page,context,url,request,ready,head,editHead,native,equal,setInjection,fixtures}){
 const profiles=[],controls=[];
 for(const fixture of fixtures){
  const first=await request(page,load(fixture)),a=command(first.state,'effective-backup-lookup','lookup',1),backup=await request(page,a);
  assert.equal(backup.durability.status,'saved');
  // Even the no-write fallback is an accepted event/revision and must persist.
  const saved=(await request(page,{action:'save'})).result;
  const b=command(backup.state,'effective-current-option','option',1);await request(page,b);
  await editHead(page,'corrupt');const corrupt=await head(page);
  await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
  const recovered=await request(page,{action:'state'});assert.equal(recovered.durability.status,'fallback');equal(recovered.state,backup.state,'connected fallback recovery');
  equal(recovered.state,native([load(fixture),a]).at(-1).state,'native lookup recovery');
  assert.match(await page.getByTestId('durability').textContent(),/previous valid checkpoint/);
  assert.equal(await page.getByTestId('effective-branch').textContent(),backup.result.branch);
  setInjection("\nconst effectivePut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){const r=effectivePut.apply(this,args);this.transaction.abort();return r;};");
  await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
  await page.getByLabel('Choose lookup slot',{exact:true}).selectOption('0');await page.getByRole('button',{name:'Look up effective plan',exact:true}).click();
  await page.getByTestId('durability').filter({hasText:'Browser save failed'}).waitFor();
  const unsaved=await request(page,{action:'state'});assert.equal(unsaved.state.revision,backup.state.revision+1);
  const accepted=unsaved.state.records.at(-1).command;equal(unsaved.state,native([{action:'load',save:saved},accepted]).at(-1).state,'unsaved explicit lookup native equality');
  equal(await head(page),corrupt,'aborted connected publication retains full head');assert.equal(unsaved.durability.durable.revision,backup.state.revision);
  setInjection('');await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
  equal((await request(page,{action:'state'})).state,backup.state,'unsaved lookup absent after reload');
  // Recover exact retry results from mixed command history after reload.
  const retry=await request(page,a);equal(retry.state,backup.state,'lookup retry after recovery');equal(retry.result,backup.result,'lookup retry exact result');
  profiles.push({fixture_sha256:backup.state.fixture_sha256,branch:backup.result.branch,recovered_state_sha256:digest(recovered.state),actual_abort_preserved:true,lookup_retry_equal:true});
 }
 controls.push('all v5 fixtures: persisted explicit lookup including no-write branch, corrupt-current fallback, visible real transaction abort, native accepted-memory state and exact retry');
 let fencing=null;
 if(fixtures.length>=3){
  const retained=fixtures[1],fresh=fixtures[2],initial=await request(page,load(retained));
  setInjection("\nconst effectivePublish=publishCheckpoint;let delayEffective=true;publishCheckpoint=async(...args)=>{if(delayEffective){delayEffective=false;await new Promise(resolve=>setTimeout(resolve,150));}return effectivePublish(...args);};");
  await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();
  const operations=[command(initial.state,'delayed-lookup','lookup',1),load(fresh)];
  const race=await page.evaluate(ops=>Promise.all(ops.map(op=>window.managementDurableRequest(op))),operations);
  assert.equal(race.every(r=>r.ok&&r.durability.status==='saved'),true);
  equal(race.map(r=>r.state),native([load(retained),...operations]).slice(1).map(r=>r.state),'delayed lookup/import serialization');
  setInjection('');await page.reload();await page.getByRole('button',{name:'Look up effective plan',exact:true}).waitFor();equal((await request(page,{action:'state'})).state,race[1].state,'fresh session recovery');
  const staleTab=await context.newPage();await ready(staleTab,url);
  try{
   const winner=await request(page,load(retained)),winnerHead=await head(page);
   assert.equal(winner.state.profile,race[1].state.profile);assert.equal(winner.state.session_id,race[1].state.session_id);
   const stale=await request(staleTab,command(race[1].state,'fresh-stale-lookup','lookup',1));
   assert.equal(stale.ok,true);assert.equal(stale.durability.status,'failed');assert.match(stale.durability.error,/conflict/);equal(await head(page),winnerHead,'stale lookup cannot overwrite another fixture');
   fencing={retained_fixture_sha256:winner.state.fixture_sha256,fresh_fixture_sha256:race[1].state.fixture_sha256,delayed_lookup_import_equal:true,stale_lookup_fenced:true};
  }finally{await staleTab.close();}
  controls.push('retained/fresh shared profile/session: delayed lookup/import serialization and stale lookup publication fencing');
 }
 return {profiles,controls,same_profile_fencing:fencing};
};
