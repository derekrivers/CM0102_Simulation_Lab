// Additional admission/compatibility controls; private fixture bytes stay local.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
module.exports=async function verifyFreshAdmission(page,root,freshEncoded,retainedEncoded){
 const fresh=JSON.parse(freshEncoded),retained=JSON.parse(retainedEncoded);
 const oracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/fresh-human-registry-oracle-v1.json')));
 assert.equal(digest(fresh),oracle.private_fixture.sha256,'fresh fixture identity');
 assert.notEqual(digest(fresh),digest(retained),'independent fixture identities');
 const load=f=>({action:'import_human_reference',fixture:JSON.stringify(f)});
 const command=(f,id,revision,slot)=>({action:'human_command',command:{session_id:f.origin+'-session-v1',command_id:id,expected_revision:revision,club_id:f.club_id,slot}});
 const native=ops=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(ops),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native admission runner');return JSON.parse(p.stdout);};
 const prefix=[load(retained),command(retained,'retained-before-fresh',0,1),{action:'save'},load(fresh),command(fresh,'fresh-after-retained',0,1),{action:'save'}];
 const expectedPrefix=native(prefix),retainedSave=expectedPrefix[2].result,freshSave=expectedPrefix[5].result;
 assert.equal(typeof retainedSave,'string');assert.equal(typeof freshSave,'string');
 const mutations=[['source_capture_sha256','0'.repeat(64)],['registry_row_sha256','0'.repeat(64)],['specimen_sha256','0'.repeat(64)],['origin','synthetic-human-regression'],['selected_slot',1]];
 const rejects=mutations.map(([key,value])=>{const fixture=structuredClone(fresh);fixture[key]=value;return load(fixture);});
 const hybrid=structuredClone(fresh);hybrid.registry_row_sha256=retained.registry_row_sha256;rejects.push(load(hybrid));
 // Repaired outer checksum cannot authorize an unreviewed embedded fixture.
 const envelope=JSON.parse(freshSave),payload=JSON.parse(envelope.payload);
 payload.fixture.registry_row_sha256=retained.registry_row_sha256;envelope.payload=JSON.stringify(payload);
 envelope.payload_bytes=Buffer.byteLength(envelope.payload);envelope.payload_sha256=createHash('sha256').update(envelope.payload).digest('hex');
 rejects.push({action:'load',save:JSON.stringify(envelope)});
 const operations=[...prefix,...rejects,{action:'load',save:retainedSave},{action:'save'},{action:'load',save:freshSave},{action:'save'},command(fresh,'fresh-continuation',1,0)];
 const expected=native(operations);
 for(let i=prefix.length;i<prefix.length+rejects.length;i++){assert.equal(expected[i].ok,false,'unqualified/hybrid identity accepted');assert.equal(digest(expected[i].state),digest(expected[i-1].state),'rejection mutated state');}
 assert.equal(expected.at(-4).result,retainedSave,'retained v3 byte roundtrip');assert.equal(expected.at(-2).result,freshSave,'fresh v3 byte roundtrip');
 const actual=await page.evaluate(async ops=>{const results=[];for(const op of ops)results.push(await window.managementRequest(op));return results;},operations);
 assert.equal(digest(actual),digest(expected),'fresh/retained native/browser identity and compatibility');
 return {operations:operations.length,native_browser_equal:true,canonical_sha256:digest(actual),fresh_fixture_sha256:digest(fresh),retained_fixture_sha256:digest(retained),
  controls:['fresh/retained profile switch','wrong source/row/specimen/origin/initial slot','hybrid retained/fresh identity','checksum-repaired embedded fixture rejection','retained and fresh v3 byte roundtrip','fresh continuation after retained restore']};
};
