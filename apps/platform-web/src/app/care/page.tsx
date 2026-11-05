"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiFailure, human, type Actor } from "../api";
import { forms, recordLabel, type ClinicalForm, type ClinicalRow, type Field, type Option, type Value } from "./forms";
import "./care.css";

interface Site { id: string; name: string; jurisdiction: string; governor: boolean; identity_status: string;
  activation: {version:number; services:string[]; active:boolean; valid_until:string; policy_reference:string} | null;
  privileges: {capabilities:string[];services:string[];valid_until:string}[] }
interface Items<T> {items:T[]; next_cursor?:string|null; as_of?:string}
type Staff = {id:string;name:string;capabilities:string[];services:string[]};
type Physical = {id:string;version:number; [key:string]:unknown};
const groups = [...new Set(forms.map(f=>f.group))];
const listKinds: Record<string,string[]> = {
  Patients: [], Encounters:["encounter"], Documentation:[], "Consent & continuity":["sharing_grant","disclosure"],
  Scheduling:["appointment"], Tasks:["task"], Diagnostics:["order","specimen","result"],
  Medicines:["medication","product"], Inpatient:["stay"], Programmes:["programme"], Procedures:["procedure"],
  Referrals:["referral"], Records:["identity_link"], "Care billing":["tariff","invoice","cash_receipt"],
};
const kindCaps: Record<string,string[]> = {
  encounter:["CARE","NURSING","REGISTER"], sharing_grant:["CARE"], disclosure:["CARE"], appointment:["REGISTER","CARE"], task:["CARE"],
  order:["CARE","DIAGNOSTICS"], specimen:["DIAGNOSTICS"], result:["CARE","DIAGNOSTICS"], medication:["CARE","PRESCRIBE","NURSING","PHARMACY"],
  product:["CARE","PRESCRIBE","NURSING","PHARMACY"], stay:["CARE","NURSING"], programme:["CARE"], procedure:["PROCEDURE"],
  referral:["CARE"], identity_link:["RECORDS"], tariff:["FINANCE","CASHIER"], invoice:["FINANCE","CASHIER"],cash_receipt:["FINANCE","CASHIER"],
};
const clean = (value:unknown) => value == null ? "Unknown / not recorded" : String(value);
const merge = (old:ClinicalRow[], next:ClinicalRow[]) => [...new Map([...old,...next].map(r=>[r.id,r])).values()];
const dateValue = (value:FormDataEntryValue | null) => new Date(String(value)).toISOString();
function setPath(target:Record<string,unknown>, path:string, value:unknown) {
  const segments=path.split("."); let current:Record<string,unknown> = target;
  segments.forEach((segment,i)=> {if(i===segments.length-1) current[segment]=value;
    else {current[segment] ??= /^\d+$/.test(segments[i+1]||"") ? [] : {}; current=current[segment] as Record<string,unknown>;}});
}
function DataView({value}:{value:Value | undefined}) {
  if (value == null || value === "") return <span className="muted">Not recorded</span>;
  if (Array.isArray(value)) return <ul>{value.map((item,i)=><li key={i}><DataView value={item}/></li>)}</ul>;
  if (typeof value === "object") return <dl className="clinical-facts">{Object.entries(value).map(([key,item])=><div key={key}><dt>{human(key)}</dt><dd><DataView value={item}/></dd></div>)}</dl>;
  return <span>{typeof value === "boolean" ? value ? "Yes" : "No" : String(value)}</span>;
}
function Input({field,options,defaultValue}:{field:Field;options:Option[];defaultValue?:string}) {
  const required=field.required !== false;
  if(field.type==="intent") return <label className="checkbox"><input type="checkbox" name={field.key} required/>{field.label}</label>;
  if(field.type==="textarea") return <label>{field.label}<textarea name={field.key} required={required} rows={3} maxLength={12000} defaultValue={defaultValue}/></label>;
  if(field.options || field.ref || field.type==="boolean") {
    const choices=field.type==="boolean" ? [{value:"true",label:"Yes"},{value:"false",label:"No"}] : field.options?.map(value=>({value,label:human(value)})) || options;
    return <label>{field.label}<select name={field.key} required={required} multiple={field.type==="multi"} defaultValue={field.type==="multi" ? [] : defaultValue || ""}>
      {field.type!=="multi" && <option value="">{required ? "Select an option" : "Not applicable / not recorded"}</option>}{choices.map(choice=><option key={choice.value} value={choice.value}>{choice.label}</option>)}
    </select></label>;
  }
  const type=field.type==="integer" || field.type==="decimal" ? "number" : field.type || "text";
  return <label>{field.label}<input name={field.key} type={type} required={required} defaultValue={defaultValue} step={field.type==="decimal" ? "any" : field.type==="integer" ? "1" : undefined} autoComplete="off" maxLength={field.type==="text" ? 160 : undefined}/></label>;
}

export default function CareWorkspace() {
  const [actor,setActor]=useState<Actor|null>(null), [checking,setChecking]=useState(true), [hidden,setHidden]=useState(false);
  const [sites,setSites]=useState<Site[]>([]), [facility,setFacility]=useState(""), [group,setGroup]=useState("Patients");
  const [rows,setRows]=useState<ClinicalRow[]>([]), [patients,setPatients]=useState<ClinicalRow[]>([]), [patient,setPatient]=useState<ClinicalRow|null>(null);
  const [encounter,setEncounter]=useState(""), [selected,setSelected]=useState<ClinicalRow|null>(null), [formId,setFormId]=useState("");
  const [staff,setStaff]=useState<Staff[]>([]), [beds,setBeds]=useState<Physical[]>([]), [lots,setLots]=useState<Physical[]>([]);
  const [privileges,setPrivileges]=useState<Physical[]>([]), [history,setHistory]=useState<Value|undefined>();
  const [error,setError]=useState(""), [success,setSuccess]=useState(""), [busy,setBusy]=useState(false), [loading,setLoading]=useState(false);
  const [query,setQuery]=useState(""), [searchCursor,setSearchCursor]=useState<string|null>(null), [cursors,setCursors]=useState<Record<string,string|null>>({});
  const [readAt,setReadAt]=useState(""); const pending=useRef(new Map<string,string>()); const viewEpoch=useRef(0);
  const site=sites.find(s=>s.id===facility), caps=[...new Set(site?.privileges.flatMap(p=>p.capabilities) || [])];
  const can=(...values:string[])=>values.some(c=>caps.includes(c));
  const prefix=`/clinical/${facility}`;
  const currentForm=forms.find(f=>f.id===formId);
  const allowedForms=forms.filter(f=>f.group===group && can(...f.capability));

  const fail=useCallback((e:unknown)=> {
    const failure=e as ApiFailure;
    if(failure.status===401){setActor(null);setRows([]);setPatient(null);setSelected(null);setHistory(undefined);pending.current.clear();}
    setError(failure.message || "The clinical service could not be reached. The action is not confirmed.");
  },[]);
  const loadSites=useCallback(async()=> {
    const result=await api<Items<Site>>("/clinical/sites");setSites(result.items);
    setFacility(current=>result.items.some(s=>s.id===current) ? current : result.items[0]?.id || "");
  },[]);
  useEffect(()=>{void api<Actor>("/auth/me").then(async value=>{setActor(value);await loadSites();}).catch(e=>{if((e as ApiFailure).status!==401)fail(e);}).finally(()=>setChecking(false));},[fail,loadSites]);
  useEffect(()=> {
    if(!actor)return;
    const check=()=> {if(document.hidden){setHidden(true);return;}void api<Actor>("/auth/me").then(()=>setHidden(false)).catch(fail);};
    const interval=window.setInterval(check,60000);document.addEventListener("visibilitychange",check);
    return ()=>{window.clearInterval(interval);document.removeEventListener("visibilitychange",check);};
  },[actor,fail]);

  const refresh=useCallback(async()=> {
    if(!facility || !actor)return;
    const epoch=viewEpoch.current;setLoading(true);setError("");
    const activeSite=sites.find(s=>s.id===facility); const available=activeSite?.privileges.flatMap(p=>p.capabilities)||[];
    const permits=(values:string[])=>values.some(c=>available.includes(c));
    try {
      if(activeSite?.governor) {
        const values=await api<Items<Physical>>(`${prefix}/privileges`); if(epoch!==viewEpoch.current)return;setPrivileges(values.items);
      }
      if(available.length || activeSite?.governor) {
        const result=await api<Items<Staff>>(`${prefix}/staff`); if(epoch!==viewEpoch.current)return;setStaff(result.items);
      }
      const jobs:(()=>Promise<void>)[]=[];
      for(const kind of listKinds[group]||[])if(permits(kindCaps[kind]||[]))jobs.push(async()=> {
        const result=await api<Items<ClinicalRow>>(`${prefix}/worklist?kind=${kind}`);
        if(epoch!==viewEpoch.current)return;
        setRows(old=>merge(old.filter(r=>r.kind!==kind || (patient && r.patient_id===patient.id)),result.items));
        setCursors(old=>({...old,[kind]:result.next_cursor||null}));setReadAt(result.as_of||new Date().toISOString());
      });
      if(permits(["REGISTER","CARE","NURSING"]))jobs.push(async()=>{const result=await api<Items<Physical>>(`${prefix}/beds`);if(epoch===viewEpoch.current)setBeds(result.items);});
      if(permits(["PHARMACY","PRESCRIBE","NURSING"]))jobs.push(async()=>{const result=await api<Items<Physical>>(`${prefix}/stock`);if(epoch===viewEpoch.current)setLots(result.items);});
      const results=await Promise.allSettled(jobs.map(job=>job()));
      const rejected=results.filter((r):r is PromiseRejectedResult=>r.status==="rejected");
      if(rejected[0])throw rejected[0].reason;
    }catch(e){fail(e);}finally{if(epoch===viewEpoch.current)setLoading(false);}
  },[facility,actor,sites,prefix,group,patient,fail]);
  useEffect(()=>{void refresh();},[refresh]);

  function changeFacility(value:string) {viewEpoch.current++;setFacility(value);setRows([]);setPatients([]);setPatient(null);setSelected(null);setEncounter("");setStaff([]);setBeds([]);setLots([]);setPrivileges([]);setFormId("");setHistory(undefined);setReadAt("");setError("");setSuccess("");setCursors({});pending.current.clear();}
  async function openPatient(row:ClinicalRow) {
    const epoch=++viewEpoch.current;setLoading(true);setFormId("");setPatient(row);setSelected(row);setHistory(undefined);setError("");setEncounter("");
    try {
      const chart=await api<{patient:ClinicalRow;items:ClinicalRow[];as_of:string;next_cursor:string|null;withheld_records:number}>(`${prefix}/patients/${row.id}/chart`);
      if(epoch!==viewEpoch.current)return;setRows(old=>merge(old,chart.items));setPatient(chart.patient);setReadAt(chart.as_of);
      const active=chart.items.filter(r=>r.kind==="encounter" && r.status!=="COMPLETED");setEncounter(active.at(-1)?.id||"");
      setCursors(old=>({...old,chart:chart.next_cursor}));
      if(chart.withheld_records)setSuccess(`${chart.withheld_records} source records are restricted under your current field permissions.`);
    }catch(e){if(epoch!==viewEpoch.current)return;if((e as ApiFailure).code==="TREATING_RELATIONSHIP_REQUIRED" || (e as ApiFailure).code==="CLINICAL_PRIVILEGE_REQUIRED")setSuccess("Demographic context selected. Clinical history requires an accepted treating assignment and current privileges.");else fail(e);}finally{if(epoch===viewEpoch.current)setLoading(false);}
  }
  async function openRecord(row:ClinicalRow) {
    setSelected(row);setHistory(undefined);setFormId("");
    if(row.kind==="encounter")setEncounter(row.id);else if(row.encounter_id)setEncounter(row.encounter_id);
    if(row.patient_id && row.patient_id!==patient?.id) {
      if(row.patient_banner)setPatient({id:row.patient_id,kind:"patient",status:"",version:0,facility_id:facility,data:row.patient_banner});
      else try {const demographic=await api<ClinicalRow>(`${prefix}/records/${row.patient_id}`);setPatient(demographic);}
      catch(e){setPatient(null);fail(e);}
    }
  }
  async function search(event:FormEvent<HTMLFormElement>, append=false) {
    event.preventDefault();setBusy(true);setError("");
    try {const response=await api<Items<ClinicalRow>>(`${prefix}/patient-search`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query,after:append?searchCursor||"":""})});setPatients(old=>append?merge(old,response.items):response.items);setSearchCursor(response.next_cursor||null);setReadAt(response.as_of||"");}
    catch(e){fail(e);}finally{setBusy(false);}
  }

  function sourceRows(kind:string):ClinicalRow[] {
    const combined=merge(rows,patients); const candidates=patient ? combined.filter(r=>!r.patient_id || r.patient_id===patient.id) : combined;
    if(kind==="patient")return merge(patients,patient?[patient]:[]);
    if(kind==="signed_note")return candidates.filter(r=>r.kind==="note" && r.status==="SIGNED");
    if(kind==="clinical_sources")return candidates.filter(r=>r.patient_id===patient?.id && !["record_error","sharing_grant","disclosure"].includes(r.kind));
    if(kind==="fulfilled")return candidates.filter(r=>({encounter:["COMPLETED"],procedure:["PERFORMED","RECOVERY","HANDED_OVER"],order:["FULFILLED"],dispense:["DISPENSED"],stay:["DISCHARGED"]} as Record<string,string[]>)[r.kind]?.includes(r.status));
    return candidates.filter(r=>r.kind===kind);
  }
  function choices(kind:string):Option[] {
    if(kind==="service")return (site?.activation?.services||[]).map(value=>({value,label:value}));
    if(kind==="staff")return [...new Map(staff.map(s=>[s.id,{value:s.id,label:`${s.name} · ${s.capabilities.map(human).join(", ") || "awaiting privileges"}`}])).values()];
    if(kind==="bed")return beds.map(b=>({value:b.id,label:`${b.ward} / ${b.label} · ${b.stay_id?"occupied":"available"}`}));
    if(kind==="lot")return lots.map(l=>({value:l.id,label:`${l.batch} · ${l.quantity} ${l.unit} · ${l.status}`}));
    return sourceRows(kind).map(r=>({value:r.id,label:`${recordLabel(r)} · ${human(r.status)} · v${r.version}`}));
  }
  async function send(path:string,body:Record<string,unknown>) {
    const encoded=JSON.stringify(body),fingerprint=prefix+path+encoded;
    const key=pending.current.get(fingerprint)||crypto.randomUUID();pending.current.set(fingerprint,key);
    const response=await api<{resource:ClinicalRow & {package?:Value};execution_state:string}>(prefix+path,{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":key},body:encoded});
    pending.current.delete(fingerprint);setSuccess(`Committed by the authoritative service. ${response.resource.kind ? human(response.resource.kind) : "Record"} saved.`);
    return response;
  }
  async function submitForm(event:FormEvent<HTMLFormElement>, spec:ClinicalForm) {
    event.preventDefault();setError("");setSuccess("");setBusy(true);const formElement=event.currentTarget;const data=new FormData(formElement);
    try {
      const targetId=String(data.get("__target")||"");const target=sourceRows(spec.target||"").find(r=>r.id===targetId);
      const body:Record<string,unknown>={};
      for(const field of spec.fields) {
        const raw=data.get(field.key);if(field.type==="intent"){body[field.key]=raw==="on";continue;}
        if(field.type==="multi"){setPath(body,field.key,data.getAll(field.key).map(String));continue;}
        if(raw==null || String(raw).trim()==="")continue;
        const value=field.type==="datetime-local" ? dateValue(raw) : field.type==="integer" ? Number(raw) : field.type==="boolean" ? raw==="true" : String(raw).trim();
        setPath(body,field.key,value);
      }
      const subject=target?.patient_id || patient?.id;
      if(spec.patient || spec.context){if(!subject)throw new Error("Select and confirm the patient context first.");body.patient_id=subject;}
      if(spec.context){const encounterId=target?.encounter_id || String(data.get("__encounter")||encounter);if(!encounterId)throw new Error("Select the correct encounter first.");body.encounter_id=encounterId;}
      let version=target?.version;
      if(spec.target==="lot")version=lots.find(l=>l.id===targetId)?.version;
      if(spec.target){if(!targetId || version==null)throw new Error("Select the current source record first.");body.expected_version=version;}
      if(body.permitted_routes)body.permitted_routes=String(body.permitted_routes).split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
      if(body.observations)(body.observations as Record<string,unknown>[]).forEach(observation=>{observation.patient_id=body.patient_id;observation.encounter_id=body.encounter_id;observation.occurred_at=body.occurred_at;});
      if(body.medication_id){const order=rows.find(r=>r.id===body.medication_id);if(!order)throw new Error("Refresh and select the current medication order.");body.expected_order_version=order.version;}
      if(body.lot_id){body.expected_lot_version=lots.find(l=>l.id===body.lot_id)?.version;}
      if(body.bed_id){body.expected_bed_version=beds.find(b=>b.id===body.bed_id)?.version;}
      if(body.invoice_id){body.expected_invoice_version=rows.find(r=>r.id===body.invoice_id)?.version;}
      if(spec.id==="administration") {
        const occurrence=await api<{occurrence_key:string}>(`${prefix}/medications/${body.medication_id}/occurrence`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({patient_id:body.patient_id,scheduled_at:body.scheduled_at})});body.occurrence_key=occurrence.occurrence_key;
      }
      const response=await send("/"+spec.path.replace("{id}",targetId),body);const row=response.resource;
      if(row.kind){setRows(old=>merge(old,[row]));setSelected(row);if(row.kind==="patient"){setPatient(row);setPatients(old=>merge(old,[row]));}if(row.kind==="encounter")setEncounter(row.id);}
      if(row.package){const blob=new Blob([JSON.stringify(row.package,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`clinical-disclosure-${row.id}.json`;link.click();URL.revokeObjectURL(url);}
      formElement.reset();setFormId("");await refresh();
    }catch(e){fail(e);}finally{setBusy(false);}
  }

  async function governance(event:FormEvent<HTMLFormElement>,path:string) {
    event.preventDefault();const element=event.currentTarget,data=new FormData(element);setBusy(true);setError("");
    try {
      const get=(key:string)=>String(data.get(key)||"").trim();
      const body=path==="/activation" ? {expected_version:site?.activation?.version||0,services:get("services").split(/\r?\n/).filter(Boolean),policy_reference:get("policy_reference"),manual_medicine_policy:get("manual_medicine_policy"),valid_from:dateValue(data.get("valid_from")),valid_until:dateValue(data.get("valid_until")),intent_confirmed:data.get("intent_confirmed")==="on"} : {account_id:get("account_id"),services:data.getAll("services"),capabilities:data.getAll("capabilities"),professional_reference:get("professional_reference"),valid_from:dateValue(data.get("valid_from")),valid_until:dateValue(data.get("valid_until")),intent_confirmed:data.get("intent_confirmed")==="on"};
      await send(path,body);element.reset();await loadSites();await refresh();
    }catch(e){fail(e);}finally{setBusy(false);}
  }

  if(checking)return <main id="main" className="auth" aria-busy="true">Checking your clinical workspace…</main>;
  if(!actor)return <main id="main" className="auth"><a className="wordmark" href="/">LW <span>CARE WORKSPACE</span></a><div className="panel"><p className="eyebrow">FACILITY CLINICAL RECORDS</p><h1>Sign in to care.</h1><p className="muted">Use your invited account and authenticator.</p>{error&&<p role="alert" className="error">{error}</p>}<form onSubmit={async event=>{event.preventDefault();const data=new FormData(event.currentTarget);setBusy(true);setError("");try{await api("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:String(data.get("email")),password:String(data.get("password")),otp:String(data.get("otp"))})});setActor(await api<Actor>("/auth/me"));await loadSites();}catch(e){fail(e);}finally{setBusy(false);}}}><label>Work email<input name="email" type="email" autoComplete="username" required/></label><label>Password<input name="password" type="password" autoComplete="current-password" maxLength={256} required/></label><label>Authenticator code<input name="otp" inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" required/></label><button disabled={busy}>Sign in securely</button></form><p className="muted">Clinical privileges are issued by your authorised clinical governor after professional verification.</p></div><a href="/">Directorate workspace</a></main>;

  const contextRows=rows.filter(r=>r.patient_id===patient?.id);
  const visibleRows=rows.filter(r=>(listKinds[group]||[]).includes(r.kind) && (!patient || !r.patient_id || r.patient_id===patient.id));
  const targetOptions=currentForm?.target==="lot" ? choices("lot") : choices(currentForm?.target||"");
  const encounters=rows.filter(r=>r.kind==="encounter" && r.patient_id===patient?.id);
  if(encounter && !encounters.some(r=>r.id===encounter))encounters.push({id:encounter,kind:"encounter",status:"CONTEXT_FROM_SCOPED_ORDER",version:0,facility_id:facility,data:{}});
  const active=!!site?.activation?.active && site.activation.valid_until>new Date().toISOString();

  return <>{hidden&&<main id="session-lock" className="auth"><h1>Clinical workspace locked.</h1><p>Your unsaved form remains in memory. Return to this window to verify your session.</p></main>}<div className="workspace care-workspace" hidden={hidden}><aside><a className="wordmark" href="/care">LW <span>CARE<br/>CLINICAL WORKSPACE</span></a><label>Facility<select disabled={busy} value={facility} onChange={event=>changeFacility(event.target.value)}><option value="">Select assigned facility</option>{sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label><nav aria-label="Clinical departments">{groups.filter(g=>forms.some(f=>f.group===g&&can(...f.capability))).map(g=><button key={g} aria-current={group===g?"page":undefined} onClick={()=>{setGroup(g);setFormId("");setHistory(undefined);}}>{g}</button>)}{site?.governor&&<button aria-current={group==="Clinical governance"?"page":undefined} onClick={()=>{setGroup("Clinical governance");setFormId("");}}>Clinical governance</button>}</nav><a href="/">Directorate workspace ↗</a><div className="account"><strong>{actor.name}</strong><small>{caps.map(human).join(" · ")||"No clinical chart privileges"}</small><button className="secondary" onClick={async()=>{try{await api("/auth/logout",{method:"POST"});setActor(null);setRows([]);setPatients([]);setPatient(null);setSelected(null);setHistory(undefined);pending.current.clear();}catch(e){fail(e);}}}>Sign out</button></div></aside>
    <main id="main"><header><div><p className="eyebrow">LW CARE · FACILITY EMR</p><h1>{group}</h1><p className="muted">{site?.name||"Select an assigned facility"}{readAt&&` · Last read ${new Date(readAt).toLocaleString()}`}</p></div><button className="secondary" disabled={loading||busy} onClick={()=>void refresh()}>{loading?"Refreshing…":"Refresh from authority"}</button></header>
      {error&&<div className="error" role="alert">{error}<p>Entered work remains in this form. Review conflicts before retrying; an uncertain request retains its operation key.</p></div>}{success&&<p className="success" role="status">{success}</p>}
      {!sites.length&&<section className="panel"><h2>No facility clinical assignment yet.</h2><p>Your Directorate administrator can invite the clinical governor and facility staff from Access. The governor records actual facility activation and verified professional privileges here.</p></section>}
      {site&&!active&&<section className="panel"><h2>Clinical activation is required.</h2><p>The clinical governor must record verified facility scope, current operating authority and validity before patient care records can be entered.</p></section>}
      {site&&active&&<div className="clinical-status"><span className="badge">Authoritative cloud service</span><span>WAN connection required for this deployment</span><span>Medication checking: adopted manual clinical review</span></div>}
      {patient&&<section className="patient-banner" aria-label="Current patient"><div><p className="eyebrow">CURRENT PATIENT · VERIFY BEFORE EVERY ACTION</p><h2>{clean(patient.data.display_name)}</h2><p>{clean(patient.data.local_identifier)} · DOB {clean(patient.data.birth_date)} · {clean(patient.data.sex)} {patient.data.provisional&&"· Provisional identity"}</p></div><button disabled={busy} className="secondary" onClick={()=>{setPatient(null);setSelected(null);setEncounter("");setHistory(undefined);setFormId("");setSuccess("");}}>Clear patient context</button></section>}
      {group==="Patients"&&active&&can("REGISTER")&&<section className="panel"><h2>Match before registering</h2><form className="search" onSubmit={event=>void search(event)}><label>Exact name words or local identifier<input value={query} onChange={event=>setQuery(event.target.value)} minLength={2} maxLength={160} required/></label><button disabled={busy}>Search local records</button></form>{patients.length>0?<div className="clinical-grid">{patients.map(row=><button className="record-card secondary" key={row.id} disabled={busy} onClick={()=>void openPatient(row)}><strong>{clean(row.data.display_name)}</strong><span>{clean(row.data.local_identifier)} · {human(row.status)}</span><small>DOB {clean(row.data.birth_date)} · {clean(row.data.sex)}</small></button>)}</div>:<p className="muted">Search results will appear here. Register an unmatched emergency patient with a provisional identity.</p>}{searchCursor&&<button className="secondary" onClick={()=>void search({preventDefault(){}} as FormEvent<HTMLFormElement>,true)}>Load more patient matches</button>}</section>}
      {active&&allowedForms.length>0&&<section className="panel clinical-actions"><h2>Clinical actions</h2><div className="actions">{allowedForms.map(f=><button key={f.id} className={formId===f.id?"":"secondary"} disabled={loading||busy} onClick={()=>{setFormId(f.id);setError("");}}>{f.title}</button>)}</div></section>}
      {active&&currentForm&&<section className="panel clinical-form" key={currentForm.id}><h2>{currentForm.title}</h2>{currentForm.explanation&&<p className="muted">{currentForm.explanation}</p>}<form onSubmit={event=>void submitForm(event,currentForm)}>
        {currentForm.target&&<label>Source record<select key={`${currentForm.id}-${selected?.id}`} name="__target" required defaultValue={targetOptions.some(o=>o.value===selected?.id)?selected?.id:""}><option value="">Select the current record</option>{targetOptions.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select></label>}
        {currentForm.context&&<label>Correct encounter<select key={`${currentForm.id}-${encounter}`} name="__encounter" required defaultValue={encounter}><option value="">Select encounter context</option>{encounters.map(r=><option key={r.id} value={r.id}>{r.id} · {human(r.status)}</option>)}</select></label>}
        {(currentForm.patient||currentForm.context)&&<p className="muted">Patient: <strong>{patient?clean(patient.data.display_name):"Select patient context first"}</strong>. Confirm the identifier in the banner before committing.</p>}
        <div className="form-grid">{currentForm.fields.map(f=><Input key={f.key} field={f} options={f.ref?choices(f.ref):[]} defaultValue={currentForm.id==="note-edit"&&selected?.kind==="note"&&typeof selected.data[f.key]==="string" ? String(selected.data[f.key]) : undefined}/>)}</div>
        <button disabled={busy||((!!currentForm.patient||!!currentForm.context)&&!patient)}>{busy?"Validating and committing…":"Commit to clinical authority"}</button><button type="button" className="secondary" onClick={()=>setFormId("")}>Close form</button>
      </form></section>}
      {active&&visibleRows.length>0&&<section className="panel"><h2>Current work and source records</h2><div className="clinical-grid">{visibleRows.map(row=><button className="record-card secondary" key={row.id} disabled={busy} onClick={()=>void openRecord(row)}><strong>{recordLabel(row)}</strong><span>{human(row.kind)} · {human(row.status)}</span><small>Version {row.version} · {row.patient_banner?.display_name?String(row.patient_banner.display_name):row.patient_id||"Facility resource"}</small></button>)}</div></section>}
      {active&&group==="Inpatient"&&<section className="panel"><h2>Ward and bed board</h2>{beds.length?<div className="clinical-grid">{beds.map(b=><div className="record-card" key={b.id}><strong>{clean(b.ward)} / {clean(b.label)}</strong><span>{b.stay_id?"Occupied":"Available"}</span><small>Version {b.version}</small></div>)}</div>:<p>No physical beds are configured.</p>}</section>}
      {active&&group==="Medicines"&&<section className="panel"><h2>Clinical stock</h2>{lots.length?<div className="clinical-grid">{lots.map(l=><button key={l.id} className="record-card secondary" onClick={()=>{setSelected({id:l.id,version:l.version,facility_id:facility,kind:"lot",status:String(l.status),data:l as Record<string,Value>});setFormId("lot-action");}}><strong>{clean(l.batch)}</strong><span>{clean(l.quantity)} {clean(l.unit)} · {clean(l.status)}</span><small>Expires {clean(l.expires_at)}</small></button>)}</div>:<p>No clinical stock receipts are recorded.</p>}</section>}
      {active&&!loading&&!visibleRows.length&&group!=="Patients"&&group!=="Clinical governance"&&<p className="muted">No permitted records are currently available for this view. Refresh after completing a workflow or select another patient context.</p>}
      {Object.entries(cursors).filter(([key,cursor])=>cursor&&key!=="chart"&&(listKinds[group]||[]).includes(key)).map(([kind,cursor])=><button className="secondary" key={kind} disabled={busy} onClick={async()=>{try{const result=await api<Items<ClinicalRow>>(`${prefix}/worklist?kind=${kind}&after=${cursor}`);setRows(old=>merge(old,result.items));setCursors(old=>({...old,[kind]:result.next_cursor||null}));}catch(e){fail(e);}}}>Load more {human(kind)} records</button>)}
      {active&&patient&&contextRows.length>0&&<section className="panel chart-section"><div className="section-heading"><div><h2>Longitudinal chart</h2><p className="muted">Source-attributed records in your permitted treatment context. No allergy assessment means unknown.</p></div><button className="secondary" onClick={()=>window.print()}>Print current permitted view</button></div>{contextRows.map(row=><details key={row.id} className={row.status==="ENTERED_IN_ERROR"?"record-restriction":""}><summary>{recordLabel(row)} · {human(row.status)} · v{row.version}</summary><small>Source {row.id} · {row.service} · Recorded {row.created_at}</small><DataView value={row.data}/><button className="secondary" disabled={busy} onClick={()=>void openRecord(row)}>Select for action</button><button className="secondary" onClick={async()=>{try{setHistory(await api<Value>(`${prefix}/records/${row.id}/history`));setSelected(row);}catch(e){fail(e);}}}>View immutable source history</button></details>)}{cursors.chart&&<button className="secondary" onClick={async()=>{try{const result=await api<Items<ClinicalRow>>(`${prefix}/patients/${patient.id}/chart?after=${cursors.chart}`);setRows(old=>merge(old,result.items));setCursors(old=>({...old,chart:result.next_cursor||null}));}catch(e){fail(e);}}}>Load earlier chart records</button>}</section>}
      {selected&&<section className="panel"><h2>Selected source · {recordLabel(selected)}</h2><p className="muted">{human(selected.status)} · version {selected.version} · {selected.id}</p><DataView value={selected.data}/></section>}
      {history&&<section className="panel"><h2>Retained source and attestation history</h2><DataView value={history}/></section>}
      {site?.governor&&group==="Clinical governance"&&<section className="panel"><h2>Clinical operating authority</h2><p>Facility identity: {human(site.identity_status)}. Record actual policy adoption and professional verification. Clinical privileges require an independent approving governor.</p><details open={!site.activation}><summary>Activate or renew facility services</summary><form onSubmit={event=>void governance(event,"/activation")}><Input field={{key:"services",label:"Actual activated service codes, one per line",type:"textarea"}} options={[]}/><Input field={{key:"policy_reference",label:"Country, custodian and clinical operating approval evidence",type:"textarea"}} options={[]}/><Input field={{key:"manual_medicine_policy",label:"Adopted manual medicine-safety process",type:"textarea"}} options={[]}/><div className="form-grid"><Input field={{key:"valid_from",label:"Effective from",type:"datetime-local"}} options={[]}/><Input field={{key:"valid_until",label:"Expires",type:"datetime-local"}} options={[]}/></div><Input field={{key:"intent_confirmed",label:"I attest the recorded operating authority and scope",type:"intent"}} options={[]}/><button disabled={busy}>Record facility activation</button></form></details><details><summary>Issue verified professional privileges</summary><form onSubmit={event=>void governance(event,"/privileges")}><Input field={{key:"account_id",label:"Activated invited facility professional",ref:"staff"}} options={choices("staff")}/><Input field={{key:"services",label:"Permitted activated services",ref:"service",type:"multi"}} options={choices("service")}/><Input field={{key:"capabilities",label:"Explicit approved capabilities",options:["REGISTER","CARE","NURSING","PRESCRIBE","PHARMACY","DIAGNOSTICS","PROCEDURE","RECORDS","SENSITIVE","FINANCE","CASHIER"],type:"multi"}} options={[]}/><Input field={{key:"professional_reference",label:"Actual licence, registration, service and verification evidence",type:"textarea"}} options={[]}/><div className="form-grid"><Input field={{key:"valid_from",label:"Valid from",type:"datetime-local"}} options={[]}/><Input field={{key:"valid_until",label:"Expires",type:"datetime-local"}} options={[]}/></div><Input field={{key:"intent_confirmed",label:"I approve these bounded privileges based on the recorded evidence",type:"intent"}} options={[]}/><button disabled={busy}>Issue verified privileges</button></form></details><h3>Issued privileges</h3>{privileges.length?privileges.map(p=><article key={p.id}><p>{staff.find(s=>s.id===p.account_id)?.name||clean(p.account_id)} · {(p.capabilities as string[]).map(human).join(", ")} · expires {clean(p.valid_until)} · {p.revoked?"Revoked":"Issued"}</p>{!p.revoked&&<button className="secondary" disabled={busy} onClick={async()=>{setBusy(true);try{await send(`/privileges/${p.id}/revoke`,{});await refresh();}catch(e){fail(e);}finally{setBusy(false);}}}>Revoke future clinical access</button>}</article>):<p>No professional privileges have been issued.</p>}</section>}
      <footer>LW Health Intelligence Platform · LW Care · {new Date().getFullYear()}</footer>
    </main></div></>;
}
