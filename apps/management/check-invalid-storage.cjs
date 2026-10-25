// Actual persistent IndexedDB heads; no storage API failure injection.
const assert=require('node:assert/strict');
module.exports=async function invalidStorage({page,context,url,request,ready,head,editHead,command,native,equal,fixture}){
 const controls=[];
 for(const change of ['malformed-head','both-invalid']){
  const initial={action:'import_registry_reference',fixture};
  const first=await request(page,initial);
  const a=command(first.state,change+'-seed-a',1),one=await request(page,a);
  const b=command(one.state,change+'-seed-b',2),stable=await request(page,b);
  assert.equal(stable.durability.status,'saved');
  const winner=await context.newPage();await ready(winner,url);
  try{
   await editHead(page,change);const invalid=await head(page);
   const expected=change==='malformed-head'?'invalid-storage-head':'no-valid-checkpoint-manual-import-or-export-required';
   // An explicit failed recovery cannot replace an existing accepted world.
   const failed=await request(page,{action:'recover'});
   assert.equal(failed.durability.status,'failed');assert.equal(failed.durability.error,expected);
   equal(failed.state,stable.state,change+' failed recovery preserves active memory');
   equal(await head(page),invalid,change+' failed recovery retains complete private head');
   await page.reload();await ready(page,url);
   const startup=await request(page,{action:'state'});
   assert.equal(startup.durability.status,'failed');assert.equal(startup.durability.error,expected);
   assert.equal(startup.durability.durable,null);
   equal(startup.state,native([{action:'state'}])[0].state,change+' failed startup keeps default memory');
   assert.match(await page.getByTestId('durability').textContent(),/Browser save failed/);
   assert.match(await page.getByTestId('durability').textContent(),new RegExp(expected));
   const action=command(startup.state,change+'-accepted-in-memory',1);
   const accepted=await request(page,action);
   assert.equal(accepted.ok,true);assert.equal(accepted.durability.status,'failed');assert.equal(accepted.durability.error,expected);
   equal(accepted.state,native([action])[0].state,change+' failed publication preserves accepted command');
   await page.getByRole('button',{name:'Save in browser',exact:true}).click();
   await page.getByTestId('durability').filter({hasText:'Accepted in memory: revision 1.'}).waitFor();
   equal((await request(page,{action:'state'})).state,accepted.state,change+' retry preserves accepted memory');
   equal(await head(page),invalid,change+' retry retains complete private bytes');
   // A previously connected tab may publish using its held token. The failed
   // tab cannot adopt that new token on retry, even after the head becomes valid.
   const published=await request(winner,command(stable.state,change+'-winner',0));
   assert.equal(published.durability.status,'saved');const publishedHead=await head(page);
   const fenced=await request(page,{action:'persist'});
   assert.equal(fenced.durability.status,'failed');assert.equal(fenced.durability.error,'storage-conflict-reopen-to-recover');
   equal(fenced.state,accepted.state,change+' conflict retains accepted memory');
   equal(await head(page),publishedHead,change+' retry cannot overwrite newer publication');
   const recovered=await request(page,{action:'recover'});
   assert.equal(recovered.durability.status,'recovered');equal(recovered.state,published.state,change+' explicit recovery rebinds');
   const continued=await request(page,command(recovered.state,change+'-after-recovery',1));
   assert.equal(continued.durability.status,'saved');
   controls.push({case:change,actual_persistent_head:true,visible_failure:true,private_head_retained:true,
    failed_recovery_preserves_memory:true,accepted_command_and_retry_preserve_memory:true,
    newer_publication_fenced:true,explicit_recovery_restores_publication:true});
  }finally{await winner.close();}
 }
 return controls;
};
