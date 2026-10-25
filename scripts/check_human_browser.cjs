// Actual WASM-worker/native human corpus. No private records printed or bundled.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
module.exports=async function verifyHuman(page,root,encodedFixture) {
 const fixture=JSON.parse(encodedFixture),session=fixture.origin+'-session-v1';
 const oracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/human-registry-oracle-v1.json')));
 const command=(id,revision,slot)=>({action:'human_command',command:{session_id:session,command_id:id,expected_revision:revision,club_id:fixture.club_id,slot}});
 const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native human runner failed');return JSON.parse(p.stdout);};
 const prefix=[{action:'import_human_reference',fixture:encodedFixture},...oracle.cases.map((c,i)=>command('human-'+i,i,c.option))];
 const revision=oracle.cases.length;
 const missing=command('missing',revision,0);missing.command.club_id=fixture.club_count;
 const wrongSession=command('wrong-session',revision,0);wrongSession.command.session_id='unqualified';
 const tampered=structuredClone(fixture);tampered.registry_index=(tampered.registry_index+1)%16;
 prefix.push(command('negative',revision,-1),command('upper',revision,2),command('stale',0,0),missing,wrongSession,
  {action:'command',command:{session_id:session,command_id:'wrong-capability',expected_revision:revision,club_id:fixture.club_id,plan_id:0}},
  {action:'import_human_reference',fixture:JSON.stringify(tampered)},{action:'save'});
 const initial=native(prefix);assert.equal(initial[0].ok,true,'human fixture admission');
 for(let i=0;i<oracle.cases.length;i++) {
  const c=oracle.cases[i],r=initial[i+1];assert.equal(r.ok,true,'human original command');
  assert.equal(r.state.selected_slot,c.selected_slot);assert.equal(r.result.old_slot,c.previous_slot);
  assert.equal(r.human_slot_location.byte_offset,c.location.byte_offset);assert.equal(r.human_slot_location.registry_index,fixture.registry_index);
  assert.equal(r.result.ordered_writes.length,1);for(const field of ['registry_offset','width','value'])assert.equal(r.result.ordered_writes[0][field],c.ordered_writes[0][field]);
 }
 const saved=initial.at(-1).result;assert.equal(JSON.parse(saved).schema_version,3);
 const next=command('continuation',revision,1);
 const legacy=fs.readFileSync(path.join(root,'crates/cm-management/tests/fixtures/legacy-plan-v1.json'),'utf8');
 const operations=[...prefix,next,{action:'reset'},{action:'load',save:saved},prefix[1],next,next,
  command('continuation',revision,0),{action:'load',save:'corrupt'},
  {action:'load',save:legacy},{action:'save'},{action:'load',save:saved},{action:'save'}];
 const expected=native(operations);
 for(let i=1;i<expected.length;i++)if(!expected[i].ok)assert.equal(digest(expected[i].state),digest(expected[i-1].state),'rejection mutation');
 assert.equal(digest(expected[prefix.length].state),digest(expected[prefix.length+5].state),'continuation/dedup');
 assert.equal(expected.at(-3).result,legacy,'v1 byte roundtrip');
 assert.equal(expected.at(-1).result,saved,'v3 byte roundtrip');
 const actual=await page.evaluate(async ops=>{const results=[];for(const op of ops)results.push(await window.managementRequest(op));return results;},operations);
 assert.equal(digest(actual),digest(expected),'human native/browser complete equality');
 return {origin:fixture.origin,fixture_sha256:digest(fixture),operations:operations.length,
  original_instruction_cases:oracle.cases.length,native_browser_equal:true,canonical_sha256:digest(actual),
  controls:['wrong slot/club/session/revision/capability','fixture tampering','v3 export/import/dedup/continuation','v1 byte roundtrip','corrupt import atomicity']};
};
