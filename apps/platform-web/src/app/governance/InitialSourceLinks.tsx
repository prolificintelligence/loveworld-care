"use client";

import {useEffect,useRef,useState,type FormEvent} from "react";
import {human,type Row} from "../api";
type Source={inspection_id:string;application_id:string;attestation_version:number;inspector_id:string;observed_at:string;observation:{outcome:string;observation:string}};
type Candidate=Partial<Source>&{eligible:boolean;reason_code?:string};
type Link=Row&{status:string;source:Source;confirmed_by:string;recorded_at:string;reason:string;retraction?:{retracted_by:string;recorded_at:string;reason:string}|null};
type Page={items:Link[];candidates:Candidate[];next_before_version:number|null;application_id:string;application_version:number;application_state:string;finding_version:number;case_version:number};
type Props={findingId:string;findingVersion:number;caseVersion:number;canConfirm:boolean;isReviewer:boolean;disabled:boolean;
 request:<T>(path:string,init?:RequestInit)=>Promise<T>;mutate:(path:string,body:Record<string,unknown>)=>Promise<Row>;refresh:()=>void;fail:(cause:unknown)=>void};

export default function InitialSourceLinks(props:Props){
 const [open,setOpen]=useState(false),[data,setData]=useState<Page|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");
 const [selected,setSelected]=useState<Candidate|null>(null),[retractId,setRetractId]=useState(""),[reason,setReason]=useState(""),[intent,setIntent]=useState(false);
 const alive=useRef(true),latest=useRef(props);latest.current=props;
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const path=`/institutional/findings/${props.findingId}/initial-source-links`,blocked=busy||props.disabled;
 function failed(cause:unknown){if(alive.current){setError((cause as Error).message);latest.current.fail(cause);}}
 async function load(before=0){setBusy(true);setError("");try{const page=await latest.current.request<Page>(path+`?before_version=${before}`);if(!alive.current)return;
  if(page.finding_version!==props.findingVersion||page.case_version!==props.caseVersion)throw new Error("The source context changed. Refresh case details before recording a link.");
  setData(old=>({...page,candidates:before&&old?[...old.candidates,...page.candidates]:page.candidates}));
 }catch(cause){failed(cause);}finally{if(alive.current)setBusy(false);}}
 async function save(event:FormEvent<HTMLFormElement>){event.preventDefault();if(!data)return;setBusy(true);setError("");setMessage("");try{
  if(!retractId&&(!selected?.inspection_id||!props.canConfirm))throw new Error("Select an actual source attestation as the current independent reviewer.");
  const body={expected_version:data.finding_version,expected_case_version:data.case_version,evidence:reason,intent_confirmed:intent,
   ...(!retractId?{application_id:data.application_id,expected_application_version:data.application_version,inspection_id:selected?.inspection_id,attestation_version:selected?.attestation_version}:{})};
  await latest.current.mutate(path+(retractId?`/${retractId}/retract`:""),body);if(!alive.current)return;
  setIntent(false);setSelected(null);setRetractId("");setMessage("The context annotation is recorded. Findings, evidence, corrective work and recognition keep their existing state.");await load();
 }catch(cause){failed(cause);}finally{if(alive.current)setBusy(false);}}
 return <section className="panel"><h4>Initial inspection source links</h4><p>Associate an actual historical unmet or unobserved initial criterion with this existing finding. A source link supplies context; it creates no finding, current evidence, resolution or recognition.</p>
 {!open?<button className="secondary" disabled={blocked} onClick={()=>{setOpen(true);void load();}}>Review initial source candidates and links</button>:<>
 {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}<button className="secondary" disabled={blocked} onClick={()=>{setSelected(null);setRetractId("");setIntent(false);void load();}}>Reload source records (clears selection)</button><button className="secondary" disabled={blocked} onClick={()=>{setOpen(false);setData(null);setSelected(null);setRetractId("");setIntent(false);setReason("");props.refresh();}}>Refresh case details (clears this local annotation)</button>
 {data&&<><section><h5>Recorded initial inspection candidates</h5><p>Current initial application: {human(data.application_state)} · version {data.application_version}. Historical attestation versions retain their original observation and inspector.</p>
 {data.candidates.length===0&&<p>No attestation candidates were returned. No source has been substituted.</p>}
 {data.candidates.map((source,index)=><article className="panel" key={`${source.attestation_version}:${index}`}><p>Attestation version {source.attestation_version}{source.observation?` · ${human(source.observation.outcome)}`:""}</p>{source.observation&&<p>{source.observation.observation}</p>}{source.inspector_id&&<p>Original inspector: {source.inspector_id} · observed {source.observed_at}</p>}
 {!source.eligible&&<p>Unavailable for a new association{source.reason_code?`: ${human(source.reason_code)}`:""}.</p>}
 {props.canConfirm&&source.eligible&&<button disabled={blocked||data.items.some(item=>item.source.inspection_id===source.inspection_id)} onClick={()=>{setSelected(source);setRetractId("");setIntent(false);}}>Select this exact source</button>}</article>)}
 {data.next_before_version&&<button disabled={blocked} onClick={()=>void load(data.next_before_version||0)}>Earlier initial attestations</button>}</section>
 {(selected||retractId)&&props.isReviewer&&<form onSubmit={save}><fieldset disabled={blocked}><legend>{retractId?"Retract a context association":"Confirm the exact historical association"}</legend>{selected&&!retractId&&<p>Selected initial attestation {selected.attestation_version} · inspection {selected.inspection_id}</p>}
 <label>Actual reason and source review<textarea required minLength={3} maxLength={12000} value={reason} onChange={event=>setReason(event.target.value)}/></label>
 <label className="checkbox"><input type="checkbox" required checked={intent} onChange={event=>setIntent(event.target.checked)}/>I intend to record this context annotation under my independent review authority</label><button disabled={blocked||!intent}>{retractId?"Record retained retraction":"Confirm source context without advancing work"}</button></fieldset></form>}
 <section><h5>Retained source associations</h5>{data.items.length===0&&<p>No source association has been recorded.</p>}{data.items.map(link=><article className="panel" key={link.id}><h5>{human(link.status)}</h5><p>Original source: {link.source.application_id} · inspection {link.source.inspection_id} · attestation {link.source.attestation_version}</p><p>{human(link.source.observation.outcome)}: {link.source.observation.observation}</p><p>Confirmed by {link.confirmed_by} at {link.recorded_at}</p><p>{link.reason}</p>{link.retraction&&<p>Retracted by {link.retraction.retracted_by} at {link.retraction.recorded_at}: {link.retraction.reason}. The original source remains retained.</p>}{props.isReviewer&&link.status==="RECORDED"&&<button disabled={blocked} onClick={()=>{setRetractId(link.id);setSelected(null);setIntent(false);}}>Retract this context link</button>}</article>)}</section>
 </>}
 </>}
 </section>;
}
