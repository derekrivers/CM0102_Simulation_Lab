import React, {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';

const worker=new Worker('worker.js');
const pending=new Map<number,{resolve:(value:any)=>void,reject:(error:any)=>void}>();
let sequence=0;
function request(operation:any):Promise<any> {return new Promise((resolve,reject)=>{
  const id=++sequence; pending.set(id,{resolve,reject}); worker.postMessage({id,operation});
});}
worker.onmessage=({data})=>{const entry=pending.get(data.id); if(!entry)return; pending.delete(data.id);data.error?entry.reject(data.error):entry.resolve(data.response);};
worker.onerror=(event)=>{for(const entry of pending.values())entry.reject(event.message);pending.clear();};
// The acceptance runner uses the same public worker protocol as the view.
(window as any).managementRequest=request;

function App(){
  const [state,setState]=useState<any>(null),[plan,setPlan]=useState('0'),[status,setStatus]=useState('Loading supported fixture…'),[busy,setBusy]=useState(false);
  async function send(operation:any){
    setBusy(true);
    try{const result=await request(operation); if(result.state){setState(result.state);setPlan(String(result.state.clubs[0].selected_plan));}
      setStatus(result.ok?'State committed · revision '+result.state.revision:'Rejected: '+result.error);return result;
    }catch(error){setStatus('Worker unavailable: '+String(error));return null;}finally{setBusy(false);}
  }
  useEffect(()=>{void send({action:'state'});},[]);
  async function save(){const result=await send({action:'save'});if(result?.ok){const url=URL.createObjectURL(new Blob([result.result],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='club-plan-slice-v1.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}
  async function load(event:React.ChangeEvent<HTMLInputElement>){const file=event.target.files?.[0];if(!file)return;if(file.size>1048576){setStatus('Rejected: save too large');return;}await send({action:'load',save:await file.text()});event.target.value='';}
  if(!state)return <main><p role="status">{status}</p></main>;
  const club=state.clubs[0];
  return <><header><span className="mark">CM / RESEARCH</span><span>Management laboratory</span><span className="revision">Revision {state.revision}</span></header>
    <main><div className="eyebrow">SUPPORTED WORKFLOW · TACTICAL PLAN SELECTION</div><h1>{club.name}</h1>
    <p className="intro">A small, stateful management experiment. Select a research plan, save your state, then reload it to continue.</p>
    <aside><strong>Fictional squad · bounded research state</strong><br/>Names and plan labels are demonstration data. The verified original path changes one club plan index; plan contents and match effects remain unqualified.</aside>
    <div className="columns"><section><div className="section-title"><h2>Squad</h2><span>{state.players.filter((p:any)=>p.club_id===club.id).length} players</span></div>
    <table><thead><tr><th>No.</th><th>Player</th><th>Position</th></tr></thead><tbody>{state.players.filter((p:any)=>p.club_id===club.id).map((p:any)=><tr key={p.id}><td>{p.id+1}</td><td>{p.name}</td><td><span className="position">{p.position}</span></td></tr>)}</tbody></table>
    </section><section><h2>Club plan</h2><p className="current">Selected: <strong data-testid="selected-plan">{state.plans[club.selected_plan].name}</strong></p>
    <form onSubmit={event=>{event.preventDefault();void send({action:'command',command:{session_id:state.session_id,command_id:'ui-'+crypto.randomUUID(),expected_revision:state.revision,club_id:club.id,plan_id:Number(plan)}});}}>
    <label htmlFor="plan">Choose a research plan</label><select id="plan" value={plan} onChange={event=>setPlan(event.target.value)} disabled={busy}>{state.plans.map((p:any)=><option value={p.id} key={p.id}>{p.name}</option>)}</select><button disabled={busy}>Apply plan</button></form>
    <p role="status" className="status">{status}</p><div className="save-row"><button type="button" className="secondary" disabled={busy} onClick={()=>void save()}>Export state</button><label className="file-button">Import state<input aria-label="Import state" type="file" accept=".json,application/json" disabled={busy} onChange={event=>void load(event)}/></label></div>
    <p className="small">Slice save v1. Compatible with this supported fixture; original game saves are unsupported.</p></section></div>
    <section className="history"><h2>Ordered effects</h2>{state.events.length===0?<p className="small">No commands yet.</p>:<ol>{state.events.map((e:any)=><li key={e.revision}>#{e.revision} · Club {e.club_id} · plan {e.old_plan+1} → {e.new_plan+1}</li>)}</ol>}</section>
    </main><footer>Rust owns every state transition · Browser presentation only · No full-game fidelity claim</footer></>;
}
createRoot(document.getElementById('root')!).render(<App/>);
