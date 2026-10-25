import React, {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';

const worker=new Worker('worker.js');
const pending=new Map<number,{resolve:(value:any)=>void,reject:(error:any)=>void}>();
let sequence=0;
function request(operation:any,storage=false):Promise<any> {return new Promise((resolve,reject)=>{
  const id=++sequence; pending.set(id,{resolve,reject}); worker.postMessage({id,operation,storage});
});}
worker.onmessage=({data})=>{const entry=pending.get(data.id); if(!entry)return; pending.delete(data.id);data.error?entry.reject(data.error):entry.resolve(data.response);};
worker.onerror=(event)=>{for(const entry of pending.values())entry.reject(event.message);pending.clear();};
// The acceptance runner uses the same public worker protocol as the view.
(window as any).managementRequest=request;
(window as any).managementDurableRequest=(operation:any)=>request(operation,true);

function App(){
  const [state,setState]=useState<any>(null),[plan,setPlan]=useState('0'),[status,setStatus]=useState('Loading supported fixture…'),[busy,setBusy]=useState(false),[clubId,setClubId]=useState<number>(0),[locations,setLocations]=useState<any[]>([]);
  const [durability,setDurability]=useState<any>(null);
  async function send(operation:any){
    setBusy(true);
    try{const result=await request(operation,true); if(result.state){setState(result.state);setLocations(result.plan_locations||[]);}if(result.durability)setDurability(result.durability);
      setStatus(result.ok?'State ready · revision '+result.state.revision:['load','import_reference','import_human_reference'].includes(operation.action)?'Rejected: invalid or unsupported state file. Your current state is unchanged.':'Rejected: '+result.error);return result;
    }catch(error){setStatus('Worker unavailable: '+String(error));return null;}finally{setBusy(false);}
  }
  useEffect(()=>{void send({action:'recover'});},[]);
  useEffect(()=>{if(!state)return;if(state.schema_version===3){setClubId(state.fixture.club_id);setPlan(String(state.selected_slot));return;}const active=state.clubs.find((c:any)=>c.id===clubId)||state.clubs[0];setClubId(active.id);setPlan(String(active.selected_plan));},[state,clubId]);
  async function save(){const result=await send({action:'save'});if(result?.ok){const url=URL.createObjectURL(new Blob([result.result],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='club-plan-slice-v'+state.schema_version+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}
  async function load(event:React.ChangeEvent<HTMLInputElement>){const file=event.target.files?.[0];if(!file)return;if(file.size>1048576){setStatus('Rejected: save too large');return;}setBusy(true);try{await send({action:'load',save:await file.text()});}catch{setStatus('Could not read state file. Current state is unchanged.');}finally{event.target.value='';setBusy(false);}}
  async function importFixture(event:React.ChangeEvent<HTMLInputElement>){const file=event.target.files?.[0];if(!file)return;if(file.size>65536){setStatus('Rejected: club fixture too large');return;}setBusy(true);try{const fixture=await file.text();const transport=JSON.parse(fixture);await send({action:'registry_row_sha256' in transport?'import_human_reference':'import_reference',fixture});}catch{setStatus('Could not read club fixture. Current state is unchanged.');}finally{event.target.value='';setBusy(false);}}
  async function loadLocalReference(human=false){setBusy(true);try{const response=await fetch(human?'human-reference-fixture.json':'reference-fixture.json',{signal:AbortSignal.timeout(10000)});if(!response.ok)throw new Error('missing');await send({action:human?'import_human_reference':'import_reference',fixture:await response.text()});}catch{setStatus('No qualified club fixture is available locally. Use Import club fixture.');}finally{setBusy(false);}}
  if(!state)return <main><p role="status">{status}</p></main>;
  const storageMessage=durability?.status==='failed'?`Accepted in memory: revision ${state.revision}. Browser save failed (${durability.error}). ${durability.durable?`Last committed checkpoint: revision ${durability.durable.revision}; it may belong to the previous imported session.`:'No committed checkpoint is confirmed.'} Export state to keep your current work.`:durability?.status==='fallback'?`Recovered previous valid checkpoint: revision ${state.revision}. The latest checkpoint was invalid.`:durability?.durable?`Saved in this browser: revision ${durability.durable.revision}.`:'No browser checkpoint yet. Apply a command or save to keep this session.';
  if(state.schema_version===3)return <><header><span className="mark">CM / RESEARCH</span><span>Human tactical registry</span><span className="revision">Revision {state.revision}</span></header><main>
    <div className="eyebrow">SUPPORTED WORKFLOW · DIRECT REGISTRY SLOT SELECTION</div><h1>{state.fixture.origin==='synthetic-human-regression'?'Fictional human club':'Captured human club'}</h1>
    <aside>Preinitialized human-manager binding · club {state.fixture.club_id}, manager {state.fixture.manager_id}. This research command selects a registry slot. Plan contents, original UI actions, appointments and match effects remain unqualified. The outer tactical getter can take a separate fallback branch.</aside>
    <section><h2>Human tactical slot</h2><p>Selected: <strong data-testid="selected-slot">Research slot {state.selected_slot+1}</strong></p><p className="small" data-testid="human-location">Registry row {state.fixture.registry_index} · slot {state.selected_slot}</p>
    <form onSubmit={event=>{event.preventDefault();void send({action:'human_command',command:{session_id:state.session_id,command_id:'ui-'+crypto.randomUUID(),expected_revision:state.revision,club_id:state.fixture.club_id,slot:Number(plan)}});}}>
    <label htmlFor="slot">Choose a research slot</label><select id="slot" value={plan} disabled={busy} onChange={event=>setPlan(event.target.value)}><option value="0">Research slot 1</option><option value="1">Research slot 2</option></select><button disabled={busy}>Apply slot</button></form>
    <p role="status" className="status">{status}</p><p className="small" data-testid="durability" aria-live="polite">{storageMessage}</p>
    <div className="save-row"><button className="secondary" disabled={busy} onClick={()=>void send({action:'persist'})}>Save in browser</button><button className="secondary" disabled={busy} onClick={()=>void save()}>Export state</button><label className="file-button">Import state<input aria-label="Import state" type="file" accept=".json,application/json" disabled={busy} onChange={event=>void load(event)}/></label><label className="file-button">Import club fixture<input aria-label="Import club fixture" type="file" accept=".json,application/json" disabled={busy} onChange={event=>void importFixture(event)}/></label><button className="secondary" disabled={busy} onClick={()=>void send({action:'reset'})}>New fictional session</button></div><p className="small">Slice save v3 · v1/v2 import remains supported. Original game saves are unsupported.</p></section>
    <section className="history"><h2>Ordered effects</h2><ol>{state.events.map((event:any)=><li key={event.revision}>#{event.revision} · slot {event.old_slot+1} → {event.new_slot+1} · registry selection byte</li>)}</ol></section>
    </main><footer>Rust owns every state transition · Direct research command · No full-game fidelity claim</footer></>;
  const club=state.clubs.find((c:any)=>c.id===clubId)||state.clubs[0];
  const manager=state.reference?.clubs.find((c:any)=>c.id===club.id);
  const location=locations.find((entry:any)=>entry.club_id===club.id)?.location;
  const captured=state.reference?.origin==='captured-bosman';
  return <><header><span className="mark">CM / RESEARCH</span><span>Management laboratory</span><span className="revision">Revision {state.revision}</span></header>
    <main><div className="eyebrow">SUPPORTED WORKFLOW · TACTICAL PLAN SELECTION</div><h1>{club.name}</h1><label htmlFor="club">Club</label><select id="club" value={club.id} disabled={busy} onChange={event=>setClubId(Number(event.target.value))}>{state.clubs.map((c:any)=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
    <p className="intro">A small, stateful management experiment. Select a research plan, save your state, then reload it to continue.</p>
    <aside><strong>{captured?'Captured club and manager context':'Fictional data · bounded research state'}</strong><br/>{captured?'These private club and manager records come from retained Bosman state, checked using official original instructions. Its retained input tree matches the clean baseline today.':'Names are demonstration data.'} Plan labels are fictional; plan contents, human-manager controls and match effects remain unqualified.</aside>
    <div className="save-row reference-controls"><button className="secondary" disabled={busy} onClick={()=>void loadLocalReference()}>Load reference clubs</button><button className="secondary" disabled={busy} onClick={()=>void loadLocalReference(true)}>Load human reference</button><label className="file-button">Import club fixture<input aria-label="Import club fixture" type="file" accept=".json,application/json" disabled={busy} onChange={event=>void importFixture(event)}/></label></div>
    <div className="columns"><section><div className="section-title"><h2>{manager?'Club context':'Squad'}</h2><span>{state.players.filter((p:any)=>p.club_id===club.id).length} players</span></div>
    {manager&&<p>Manager: <strong data-testid="manager-name">{manager.manager_name}</strong></p>}
    {manager&&<p className="small">Manager-linked ordinary club. Squad records have not been imported.</p>}
    <table><thead><tr><th>No.</th><th>Player</th><th>Position</th></tr></thead><tbody>{state.players.filter((p:any)=>p.club_id===club.id).map((p:any)=><tr key={p.id}><td>{p.id+1}</td><td>{p.name}</td><td><span className="position">{p.position}</span></td></tr>)}{!state.players.some((p:any)=>p.club_id===club.id)&&<tr><td colSpan={3}>No supplied squad records for this club.</td></tr>}</tbody></table>
    </section><section><h2>Club plan</h2><p className="current">Selected: <strong data-testid="selected-plan">{state.plans[club.selected_plan].name}</strong></p>{location&&<p className="small" data-testid="plan-location">Resolved bank: {location.bank} · index {location.index}</p>}
    <form onSubmit={event=>{event.preventDefault();void send({action:'command',command:{session_id:state.session_id,command_id:'ui-'+crypto.randomUUID(),expected_revision:state.revision,club_id:club.id,plan_id:Number(plan)}});}}>
    <label htmlFor="plan">Choose a research plan</label><select id="plan" value={plan} onChange={event=>setPlan(event.target.value)} disabled={busy}>{state.plans.map((p:any)=><option value={p.id} key={p.id}>{p.name}</option>)}</select><button disabled={busy}>Apply plan</button></form>
    <p role="status" className="status">{status}</p>
    <p className="small" data-testid="durability" aria-live="polite">{storageMessage}</p>
    <div className="save-row"><button type="button" className="secondary" disabled={busy} onClick={()=>void send({action:'persist'})}>Save in browser</button><button type="button" className="secondary" disabled={busy} onClick={()=>void save()}>Export state</button><label className="file-button">Import state<input aria-label="Import state" type="file" accept=".json,application/json" disabled={busy} onChange={event=>void load(event)}/></label></div>
    <p className="small">Slice save v{state.schema_version}. Version 1 exports remain supported. Original game saves are unsupported.</p></section></div>
    <section className="history"><h2>Ordered effects</h2>{state.events.length===0?<p className="small">No commands yet.</p>:<ol>{state.events.map((e:any)=><li key={e.revision}>#{e.revision} · Club {e.club_id} · plan {e.old_plan+1} → {e.new_plan+1}</li>)}</ol>}</section>
    </main><footer>Rust owns every state transition · Browser presentation only · No full-game fidelity claim</footer></>;
}
createRoot(document.getElementById('root')!).render(<App/>);
