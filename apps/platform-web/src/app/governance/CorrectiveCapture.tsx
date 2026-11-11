"use client";

import {useEffect,useRef,useState,type FormEvent} from "react";
import {human,type Row} from "../api";

type Key="finding_id"|"required_action"|"owner_team_id"|"due_at"|"response"|"evidence_refs"|"review_result";
type Answer={mode:"omit"|"value"|"absence";value:string;reason:string;explanation:string};
type Context={actor_id:string;authority_node_id:string;facility_or_unit_id:string;finding_version:number;case_version:number;case_state:string};
type Page={items:Row[];next_before_id:string|null;context:Context;recorded_source_values:Partial<Record<Key,unknown>>};
type Props={findingId:string;findingVersion:number;caseVersion:number;actorId:string;canWrite:boolean;isReviewer:boolean;disabled:boolean;
  request:<T>(path:string,init?:RequestInit)=>Promise<T>;mutate:(path:string,body:Record<string,unknown>)=>Promise<Row>;refresh:()=>void;fail:(cause:unknown)=>void};
const fields:{key:Key;label:string;required?:boolean}[]=[
  {key:"finding_id",label:"Source finding",required:true},{key:"required_action",label:"Agreed corrective action",required:true},
  {key:"owner_team_id",label:"Responsible delivery team",required:true},{key:"due_at",label:"Adopted deadline with timezone",required:true},
  {key:"response",label:"Applicant response"},{key:"evidence_refs",label:"Resolution evidence references"},{key:"review_result",label:"Independent review and reason"}];
const reasons=["unknown","not_assessed","not_applicable","not_available","declined"];
const blank=()=>Object.fromEntries(fields.map(({key})=>[key,{mode:"omit",value:"",reason:"",explanation:""}])) as Record<Key,Answer>;
function answerText(value:unknown){
  if(Array.isArray(value))return value.length?value.join("; "):"No references listed";
  if(value&&typeof value==="object"){const absent=value as {absent_reason:string;explanation?:string};return human(absent.absent_reason)+(absent.explanation?` — ${absent.explanation}`:"");}
  return String(value);
}

export default function CorrectiveCapturePanel(props:Props){
  const [open,setOpen]=useState(false),[data,setData]=useState<Page|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[message,setMessage]=useState("");
  const [answers,setAnswers]=useState(blank),[stage,setStage]=useState("draft"),[reason,setReason]=useState(""),[intent,setIntent]=useState(false),[recordedAt,setRecordedAt]=useState(""),[sources,setSources]=useState("");
  const alive=useRef(true),latest=useRef(props);latest.current=props;
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  const path=`/institutional/findings/${props.findingId}/corrective-captures`;
  const blocked=busy||props.disabled;
  function failed(cause:unknown){if(!alive.current)return;setError((cause as Error).message);latest.current.fail(cause);}
  async function load(before=""){
    setBusy(true);setError("");
    try{const page=await latest.current.request<Page>(path+(before?`?before_id=${before}`:""));
      if(!alive.current)return;
      if(page.context.actor_id!==props.actorId||page.context.finding_version!==props.findingVersion||page.context.case_version!==props.caseVersion)throw new Error("The source changed. Refresh the case details before recording a form.");
      setData(old=>({...page,items:before&&old?[...old.items,...page.items]:page.items}));
    }catch(cause){failed(cause);}finally{if(alive.current)setBusy(false);}
  }
  function change(key:Key,patch:Partial<Answer>){setAnswers(old=>({...old,[key]:{...old[key],...patch}}));}
  function copyRecorded(){if(!data)return;setAnswers(old=>{const updated={...old};for(const {key} of fields){const value=data.recorded_source_values[key];if(value===undefined||(key==="review_result"&&!props.isReviewer))continue;updated[key]={...old[key],mode:"value",value:Array.isArray(value)?value.join("\n"):String(value)};}return updated;});}
  async function save(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(!data)return;setBusy(true);setError("");setMessage("");
    try{const values:Record<string,unknown>={};for(const {key,required} of fields){const answer=answers[key];
      if(answer.mode==="omit"){if(stage==="submitted"&&required)throw new Error("Choose a value or an absence reason for every required submitted field.");continue;}
      if(answer.mode==="absence"){if(!answer.reason)throw new Error("Choose the actual absence reason.");values[key]={absent_reason:answer.reason,...(answer.explanation?{explanation:answer.explanation}:{})};}
      else values[key]=key==="evidence_refs"?answer.value.split(/\r?\n/).map(value=>value.trim()).filter(Boolean):answer.value;
    }
      const form={form_id:"LWH-FRM-010",schema_version:"1.0.0",stage,authority_node_id:data.context.authority_node_id,actor_id:data.context.actor_id,facility_or_unit_id:data.context.facility_or_unit_id,answers:values,
        ...(recordedAt?{recorded_at:recordedAt}:{}),...(sources.trim()?{source_refs:sources.split(/\r?\n/).map(value=>value.trim()).filter(Boolean)}:{})};
      const result=await latest.current.mutate(path,{expected_version:data.context.finding_version,expected_case_version:data.context.case_version,evidence:reason,intent_confirmed:intent,form});
      if(!alive.current)return;
      setIntent(false);setMessage(`Form record ${result.id} is saved. Plans, findings and recognition keep their current state.`);
      await load();
    }catch(cause){failed(cause);}finally{if(alive.current)setBusy(false);}
  }
  return <section className="panel"><h4>Corrective form capture</h4><p>Record explicit answers or absence reasons against this finding. Form submission does not agree a plan, resolve a finding or authorize recognition.</p>
    {!open?<button className="secondary" disabled={blocked} onClick={()=>{setOpen(true);void load();}}>Open form capture and history</button>:<>
      {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
      <button className="secondary" disabled={blocked} onClick={props.refresh}>Refresh case details (clears this local form)</button>
      {data&&props.canWrite&&<form onSubmit={save}><fieldset disabled={blocked}><legend>FRM-010 answers</legend>
        <label>Record stage<select value={stage} onChange={event=>setStage(event.target.value)}><option value="draft">Draft notes — values are unverified</option><option value="submitted">Submitted form — values must match recorded sources</option></select></label>
        <p>Unanswered fields stay omitted. Absence reasons are your declarations, distinct from an empty reference list. Submitted forms require the first four fields, using an actual value or an explicit absence reason.</p>
        <button type="button" className="secondary" onClick={copyRecorded}>Use actual recorded source values</button>
        {fields.map(field=>{const answer=answers[field.key];return <fieldset key={field.key}><legend>{field.label}{field.required?" (required when submitted)":""}</legend>
          <label>Answer status<select value={answer.mode} onChange={event=>change(field.key,{mode:event.target.value as Answer["mode"]})}><option value="omit">Unanswered — omit this field</option><option value="value">Actual value</option><option value="absence">Explicit absence reason</option></select></label>
          {answer.mode==="value"&&<label>{field.label}{field.key==="evidence_refs"?" (one identifier per line; empty means none listed)":""}<textarea required={field.key!=="evidence_refs"} maxLength={20000} rows={field.key==="finding_id"||field.key==="owner_team_id"||field.key==="due_at"?1:3} value={answer.value} onChange={event=>change(field.key,{value:event.target.value})}/></label>}
          {answer.mode==="absence"&&<><label>Absence reason<select required value={answer.reason} onChange={event=>change(field.key,{reason:event.target.value})}><option value="">Choose an actual reason</option>{reasons.map(value=><option key={value} value={value}>{human(value)}</option>)}</select></label><label>Explanation (optional)<textarea maxLength={4000} value={answer.explanation} onChange={event=>change(field.key,{explanation:event.target.value})}/></label></>}
        </fieldset>;})}
        {!props.isReviewer&&<p>Only the assigned independent reviewer can submit an actual review result. A missing review can be recorded with an explicit absence reason.</p>}
        <label>Stated form time with timezone (optional)<input value={recordedAt} onChange={event=>setRecordedAt(event.target.value)} placeholder="2026-11-11T10:00:00+00:00"/></label>
        <label>Source references (optional, one per line)<textarea value={sources} onChange={event=>setSources(event.target.value)}/></label>
        <label>Actual reason for recording this form<textarea required minLength={3} maxLength={12000} value={reason} onChange={event=>setReason(event.target.value)}/></label>
        <label className="checkbox"><input type="checkbox" required checked={intent} onChange={event=>setIntent(event.target.checked)}/>I intend to record this form under my authenticated authority</label>
        <button disabled={blocked||!intent}>Record form without advancing the finding</button>
      </fieldset></form>}
      {data&&<section><h4>Recorded form history</h4>{data.items.length===0&&<p>No form captures have been recorded for this finding.</p>}{data.items.map(item=>{const form=item.form as {stage:string;answers:Record<string,unknown>;recorded_at?:string};const binding=item.source_binding as {finding_version:number;case_version:number};return <article className="panel" key={item.id}><h5>{form.stage==="draft"?"Unverified draft record":"Submitted form record"}</h5><p>{String(item.recorded_at)} · recorded by {String(item.recorded_by)}</p><p>Finding version {binding.finding_version}; case version {binding.case_version}. This record did not advance the workflow.</p><dl>{fields.map(field=><div key={field.key}><dt>{field.label}</dt><dd style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{field.key in form.answers?answerText(form.answers[field.key]):"Unanswered"}</dd></div>)}</dl><p>Recording reason: {String(item.reason)}</p>{form.recorded_at&&<p>Stated form time: {form.recorded_at}</p>}</article>;})}
        {data.next_before_id&&<button disabled={blocked} onClick={()=>void load(data.next_before_id||"")}>Earlier form captures</button>}
      </section>}
    </>}
  </section>;
}
