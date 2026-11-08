"use client";

import {useCallback,useEffect,useRef,useState,type FormEvent} from "react";
import {api,human} from "../api";

type Run={id:string;kind?:string;source_id:string|null;outcome:string;started_at:string;completed_at:string;summary:Record<string,unknown>};
type Status={latest:{backup:Run|null;restore:Run|null;reconciliation:Run|null};as_of:string;backup_cadence:string;recovery_targets:string;independent_off_account_copy:string;operating_acceptance:string};
type Page={items:Run[];next_cursor:string|null};

function Facts({value}:{value:unknown}){
  if(value===null||value===undefined)return <span>Not recorded</span>;
  if(Array.isArray(value))return <ul>{value.map((item,index)=><li key={index}><Facts value={item}/></li>)}</ul>;
  if(typeof value==="object")return <dl>{Object.entries(value).map(([key,item])=><div key={key}><dt>{human(key)}</dt><dd><Facts value={item}/></dd></div>)}</dl>;
  return <span>{typeof value==="boolean"?value?"Yes":"No":String(value)}</span>;
}

export function ReliabilityPanel({onFailure}:{onFailure:(cause:unknown)=>void}){
  const [status,setStatus]=useState<Status|null>(null),[runs,setRuns]=useState<Run[]>([]),[cursor,setCursor]=useState<string|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  const operation=useRef<{body:string;key:string}|null>(null);
  const refresh=useCallback(async()=>{setLoading(true);try{const [state,page]=await Promise.all([api<Status>("/operations/reliability"),api<Page>("/operations/assurance-runs")]);setStatus(state);setRuns(page.items);setCursor(page.next_cursor);}catch(cause){onFailure(cause);}finally{setLoading(false);}},[onFailure]);
  useEffect(()=>{void refresh();},[refresh]);
  async function reconcile(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=new FormData(event.currentTarget),body=JSON.stringify({evidence:String(form.get("evidence")),intent_confirmed:form.get("intent")==="on"});if(operation.current?.body!==body)operation.current={body,key:crypto.randomUUID()};setBusy(true);setMessage("");try{await api("/operations/reconciliation",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":operation.current.key},body});operation.current=null;setMessage("The executed observation is recorded. Review any exceptions and their source workflows; this action does not close care or approve service resumption.");await refresh();}catch(cause){onFailure(cause);}finally{setBusy(false);}}
  return <section aria-label="Recovery and integrity evidence" aria-busy={loading||busy}>
    <section className="panel"><h2>Observed recovery and data integrity</h2><p>Backup, isolated restoration and clinical completion are separate facts. A successful restore rehearsal does not activate a replacement service or close outstanding work.</p><button className="secondary" disabled={loading||busy} onClick={()=>void refresh()}>Refresh recorded evidence</button>{loading&&<p role="status">Loading current evidence...</p>}{!loading&&!status&&<p role="status">Evidence could not be loaded. Refresh to retry; no recovery status has been inferred.</p>}{status&&<p className="muted">Read at {new Date(status.as_of).toLocaleString()}. Backups are operator-managed; automated backup scheduling, independently held copies and adopted recovery targets require their own qualification.</p>}</section>
    {status&&([['backup','Archive'],['restore','Isolated restoration'],['reconciliation','Integrity observation']] as const).map(([key,label])=>{const run=status.latest[key];return <section className="panel" key={key}><h2>{label}</h2>{!run?<p>No completed evidence is recorded for this activity. Readiness has not been established.</p>:<><p><strong>{human(run.outcome)}</strong></p><p>Recorded {new Date(run.completed_at).toLocaleString()}</p><details><summary>Review actual measurements and limitations</summary><Facts value={run.summary}/></details><p className="muted">Evidence reference: {run.id}{run.source_id?` · Source archive: ${run.source_id}`:""}</p></>}</section>;})}
    <section className="panel"><h2>Run an integrity observation</h2><p>Checks cover central ledger balance, stock movements, task indexes, job leases and unresolved ownership. Results contain aggregate counts. Source records remain unchanged; each SQL check observes its own committed snapshot.</p><form onSubmit={event=>void reconcile(event)}><label>Reason and actual operating reference<textarea name="evidence" required minLength={3} maxLength={12000} rows={3}/></label><label className="checkbox"><input name="intent" type="checkbox" required/>I intend to record this observation under my current authority.</label><button disabled={busy||loading}>Run and record checks</button></form>{message&&<p role="status">{message}</p>}</section>
    <section className="panel"><h2>Recorded history</h2>{!loading&&runs.length===0&&<p>No operating evidence has been recorded.</p>}{runs.map(run=><article className="panel" key={run.id}><strong>{human(run.kind||"Observation")} · {human(run.outcome)}</strong><p>{new Date(run.completed_at).toLocaleString()}</p><details><summary>Measurements for {run.id}</summary><Facts value={run.summary}/></details></article>)}{cursor&&<button disabled={busy||loading} className="secondary" onClick={async()=>{setBusy(true);try{const page=await api<Page>(`/operations/assurance-runs?after=${encodeURIComponent(cursor)}`);setRuns(old=>[...new Map([...old,...page.items].map(run=>[run.id,run])).values()]);setCursor(page.next_cursor);}catch(cause){onFailure(cause);}finally{setBusy(false);}}}>Load more recorded history</button>}</section>
  </section>;
}
