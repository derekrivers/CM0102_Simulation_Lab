// Full native/browser comparison; diagnostics contain hashes, never private records.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process'),{createHash}=require('node:crypto');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const hash=v=>createHash('sha256').update(v).digest('hex');
const digest=v=>hash(JSON.stringify(canonical(v)));
module.exports=async function verifyReference(page,root,out,encodedFixture) {
 const fixture=JSON.parse(encodedFixture),session=fixture.origin+'-club-session-v1';
 const oracle=JSON.parse(fs.readFileSync(path.join(root,'docs/research/evidence/manager-bound-plan-oracle-v1.json')));
 const command=(id,revision,club,plan)=>({action:'command',command:{session_id:session,command_id:id,expected_revision:revision,club_id:club,plan_id:plan}});
 const native=operations=>{const p=spawnSync(path.join(root,'target/debug/management-corpus'),[],{input:JSON.stringify(operations),encoding:'utf8',maxBuffer:32*1024*1024});assert.equal(p.status,0,'native reference runner failed');return JSON.parse(p.stdout);};
 const prefix=[{action:'import_reference',fixture:encodedFixture},...oracle.cases.map((c,i)=>command('ref-'+i,i,fixture.clubs[c.club_label].id,c.plan_index))];
 const rev=oracle.cases.length,club=fixture.clubs[0].id,total=fixture.first_bank_count+fixture.second_bank_count;
 prefix.push(command('negative',rev,club,-1),command('upper',rev,club,total),command('missing',rev,fixture.club_count,0),command('stale',0,club,0));
 const tampered=structuredClone(fixture);tampered.clubs[0].manager_id=fixture.staff_count-16;
 prefix.push({action:'import_reference',fixture:JSON.stringify(tampered)},{action:'save'});
 const saved=native(prefix).at(-1).result;
 assert.equal(typeof saved,'string','reference fixture was not admitted');
 const next=command('continuation',rev,club,total-1);
 const operations=[...prefix,next,{action:'load',save:saved},prefix[1],next,next,{action:'load',save:'invalid'}];
 const expected=native(operations);
 for(let i=0;i<expected.length;i++)if(!expected[i].ok){assert.equal(digest(expected[i].state),digest(expected[i-1].state),'invalid operation mutated state');}
 assert.equal(digest(expected[prefix.length].state),digest(expected.at(-2).state),'continuation/dedup mismatch');
 const actual=await page.evaluate(async ops=>{const result=[];for(const op of ops)result.push(await window.managementRequest(op));return result;},operations);
 assert.equal(digest(actual),digest(expected),'reference native/browser state/events/save mismatch');

 // A pending local-file fetch must lock all mutation/import controls immediately.
 await page.reload();await page.getByRole('button',{name:'Apply plan',exact:true}).waitFor();
 let release;const gate=new Promise(resolve=>release=resolve);
 await page.route('**/reference-fixture.json',async route=>{await gate;await route.fulfill({contentType:'application/json',body:encodedFixture});});
 await page.getByRole('button',{name:'Load reference clubs'}).click();
 assert.equal(await page.getByRole('button',{name:'Apply plan',exact:true}).isDisabled(),true);
 assert.equal(await page.getByLabel('Club',{exact:true}).isDisabled(),true);
 assert.equal(await page.getByRole('button',{name:'Export state'}).isDisabled(),true);
 release();await page.getByTestId('manager-name').waitFor();
 assert.equal(hash(await page.getByTestId('manager-name').textContent()),hash(fixture.clubs[0].manager_name),'manager projection mismatch');
 await page.getByLabel('Club',{exact:true}).selectOption(String(fixture.clubs[1].id));
 await page.getByLabel('Choose a research plan').selectOption(String(total-1));
 await page.getByRole('button',{name:'Apply plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
 assert.equal((await page.getByTestId('plan-location').textContent()).includes('second'),true);
 const change=await page.evaluate(()=>window.managementRequest({action:'state'}));
 assert.equal(change.state.clubs[1].selected_plan,total-1);assert.equal(change.state.clubs[0].selected_plan,fixture.clubs[0].selected_plan);
 const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Export state'}).click();
 const download=await downloadEvent;const savePath=path.join(out,fixture.origin+'-slice-v2.json');await download.saveAs(savePath);
 await page.getByLabel('Choose a research plan').selectOption('0');await page.getByRole('button',{name:'Apply plan',exact:true}).click();await page.getByRole('status').filter({hasText:'revision 2'}).waitFor();
 await page.getByLabel('Import state',{exact:true}).setInputFiles(savePath);await page.getByRole('status').filter({hasText:'revision 1'}).waitFor();
 const restored=await page.evaluate(()=>window.managementRequest({action:'state'}));assert.equal(digest(restored.state),digest(change.state),'UI v2 restore mismatch');
 await page.getByLabel('Import club fixture',{exact:true}).setInputFiles({name:'unqualified.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(tampered))});
 await page.getByRole('status').filter({hasText:'Rejected:'}).waitFor();
 const unchanged=await page.evaluate(()=>window.managementRequest({action:'state'}));assert.equal(digest(unchanged.state),digest(restored.state));
 await page.unroute('**/reference-fixture.json');
 // Screenshots of captured names belong only in ignored/private test output.
 await page.screenshot({path:path.join(out,fixture.origin+'-management.png'),fullPage:true});
 return {origin:fixture.origin,fixture_sha256:digest(fixture),operations:operations.length,original_instruction_cases:oracle.cases.length,
   native_browser_equal:true,canonical_sha256:digest(actual),ui_controls:['pending import locks mutations','sparse club selection','manager projection','second bank resolution','v2 export/import continuation','unqualified fixture preserves state']};
};
