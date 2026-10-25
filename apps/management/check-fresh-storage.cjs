// Real IndexedDB identity, recovery and import races for the two private fixtures.
const fs=require('node:fs'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
module.exports=async function verifyFreshStorage({page,context,url,request,ready,head,editHead,command,native,equal,setInjection}){
 const freshFixture=fs.readFileSync(process.env.FRESH_HUMAN_REFERENCE_FIXTURE,'utf8');
 const retainedFixture=fs.readFileSync(process.env.HUMAN_REFERENCE_FIXTURE,'utf8');
 const loadFixture=fixture=>({action:'import_human_reference',fixture});
 const freshHash=digest(JSON.parse(freshFixture)),retainedHash=digest(JSON.parse(retainedFixture)),controls=[];
 let fresh=await request(page,loadFixture(freshFixture));
 fresh=await request(page,command(fresh.state,'fresh-backup',1));
 const backupSave=(await request(page,{action:'save'})).result;
 await request(page,command(fresh.state,'fresh-current',0));
 await editHead(page,'corrupt');const corruptHead=await head(page);
 await page.reload();await page.getByRole('button',{name:'Apply slot',exact:true}).waitFor();
 const fallback=await request(page,{action:'state'});
 assert.equal(fallback.durability.status,'fallback');equal(fallback.state,fresh.state,'fresh corrupt checkpoint fallback');
 assert.equal(fallback.state.fixture_sha256,freshHash);
 assert.match(await page.getByTestId('durability').textContent(),/previous valid checkpoint/);
 setInjection("\nconst freshPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){const r=freshPut.apply(this,args);this.transaction.abort();return r;};");
 await page.reload();await page.getByRole('button',{name:'Apply slot',exact:true}).waitFor();
 await page.getByLabel('Choose a research slot').selectOption('0');await page.getByRole('button',{name:'Apply slot',exact:true}).click();
 await page.getByTestId('durability').filter({hasText:'Browser save failed'}).waitFor();
 const unsaved=await request(page,{action:'state'});assert.equal(unsaved.state.revision,fresh.state.revision+1);
 assert.equal(unsaved.durability.durable.fixture_sha256,freshHash);
 assert.equal(unsaved.durability.durable.revision,fresh.state.revision);
 equal(await head(page),corruptHead,'fresh failed publication preserves entire previous head');
 const last=unsaved.state.records.at(-1).command;
 equal(unsaved.state,native([{action:'load',save:backupSave},{action:'human_command',command:last}]).at(-1).state,'fresh accepted unsaved command equals native');
 setInjection('');await page.reload();await page.getByRole('button',{name:'Apply slot',exact:true}).waitFor();
 equal((await request(page,{action:'state'})).state,fresh.state,'fresh unsaved state absent after reload');
 controls.push('fresh corrupt-current fallback and visible actual transaction-abort failure preserve previous checkpoint and native in-memory state');

 // Both private fixtures share profile/session names. Exact fixture identity
 // and host session must still distinguish imported checkpoints.
 const retained=await request(page,loadFixture(retainedFixture));
 const retainedHost=(await head(page)).current.host_session;
 setInjection("\nconst importedPublish=publishCheckpoint;let firstImportWrite=true;publishCheckpoint=async(...args)=>{if(firstImportWrite){firstImportWrite=false;await new Promise(resolve=>setTimeout(resolve,150));}return importedPublish(...args);};");
 await page.reload();await page.getByRole('button',{name:'Apply slot',exact:true}).waitFor();
 const operations=[command(retained.state,'retained-delayed-before-fresh',1),loadFixture(freshFixture)];
 const race=await page.evaluate(ops=>Promise.all(ops.map(op=>window.managementDurableRequest(op))),operations);
 assert.equal(race.every(r=>r.durability.status==='saved'),true);
 equal(race.map(r=>r.state),native([loadFixture(retainedFixture),...operations]).slice(1).map(r=>r.state),'same-profile ordered native publication');
 const published=await head(page);assert.equal(published.current.identity.fixture_sha256,freshHash);
 assert.notEqual(published.current.host_session,retainedHost);
 setInjection('');await page.reload();await page.getByRole('button',{name:'Apply slot',exact:true}).waitFor();
 equal((await request(page,{action:'state'})).state,race[1].state,'same-profile delayed writer recovery');
 controls.push('delayed retained command completes before fresh same-profile import; fresh fixture and new host session survive reload');

 const staleTab=await context.newPage();await ready(staleTab,url);
 const winner=await request(page,loadFixture(retainedFixture)),winnerHead=await head(page);
 assert.equal(winner.state.profile,race[1].state.profile);assert.equal(winner.state.session_id,race[1].state.session_id);
 assert.equal(winnerHead.current.identity.fixture_sha256,retainedHash);
 assert.notEqual(winnerHead.current.host_session,published.current.host_session);
 const stale=await request(staleTab,command(race[1].state,'fresh-stale-after-retained-import',1));
 assert.equal(stale.ok,true);assert.equal(stale.durability.status,'failed');assert.match(stale.durability.error,/conflict/);
 equal(await head(page),winnerHead,'same-profile stale fresh tab cannot overwrite retained import');await staleTab.close();
 controls.push('same-profile and same-Rust-session stale tab cannot overwrite a newer different-fixture import');
 return {fresh_fixture_sha256:freshHash,retained_fixture_sha256:retainedHash,controls};
};
