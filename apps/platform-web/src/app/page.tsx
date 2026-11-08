"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiFailure, human, text, type Actor, type Row } from "./api";
import IntegrationControls from "./IntegrationControls";

const sections = ["Facilities", "Applications", "Organisation", "Standards", "Access", "Audit"] as const;
type Section = typeof sections[number];
const siteTypes = ["COMMUNITY_PRIMARY", "INPATIENT_HOSPITAL", "MATERNAL_CHILD", "SPECIALIST_DIAGNOSTIC"];
const roles = ["PLATFORM_ADMIN", "REGISTRY_STEWARD", "FACILITY_ADMIN", "ZONE_COORDINATOR", "REGIONAL_COORDINATOR", "INSPECTOR", "STANDARDS_REVIEWER", "STANDARDS_DECIDER", "CLINICAL_GOVERNOR", "CLINICAL_STAFF", "DATA_GOVERNOR", "REPORTING_OFFICER", "DATA_REVIEWER", "DATA_ANALYST", "EXECUTIVE_VIEWER", "PROGRAMME_OWNER", "SAFETY_REPORTER", "SAFETY_REVIEWER", "IDENTITY_REVIEWER", "PRIVACY_OFFICER", "FINANCE_GOVERNOR", "CONTENT_EDITOR", "POLICY_OWNER", "CONTENT_PUBLISHER"];
function Field({ name, label, type = "text", required = true }: {name: string; label: string; type?: string; required?: boolean}) {
  return <label>{label}<input name={name} type={type} required={required} autoComplete="off" /></label>;
}
function Select({ name, label, rows }: {name: string; label: string; rows: {value: string; label: string}[]}) {
  return <label>{label}<select name={name} required defaultValue=""><option value="" disabled>Select {label.toLowerCase()}</option>{rows.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</select></label>;
}
const options = (values: readonly string[]) => values.map(value => ({value, label: human(value)}));
const rowOptions = (rows: Row[]) => rows.map(r => ({value: r.id, label: r.name || text(r, "name")}));
const get = (data: FormData, key: string) => String(data.get(key) || "").trim();
const date = (data: FormData, key: string) => new Date(get(data, key)).toISOString();

export default function Platform() {
  const [actor, setActor] = useState<Actor | null>(null);
  const [checking, setChecking] = useState(true);
  const [section, setSection] = useState<Section>("Facilities");
  const [rows, setRows] = useState<Row[]>([]);
  const [units, setUnits] = useState<Row[]>([]);
  const [research, setResearch] = useState<Row[]>([]);
  const [operators, setOperators] = useState<Row[]>([]);
  const [criteria, setCriteria] = useState<Row[]>([]);
  const [accounts, setAccounts] = useState<Row[]>([]);
  const [grants, setGrants] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selected, setSelected] = useState<Row | null>(null);
  const [dossier, setDossier] = useState<Record<string, unknown> | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const pending = useRef(new Map<string, string>());
  const dataScope = useRef(0);
  const [online, setOnline] = useState(true);
  const [criterionCount, setCriterionCount] = useState(1);

  useEffect(() => {
    api<Actor>("/auth/me").then(setActor).catch(e => { if (!(e instanceof ApiFailure && e.status === 401)) setError(e.message); }).finally(() => setChecking(false));
    const update = () => setOnline(navigator.onLine);
    update(); window.addEventListener("online", update); window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  const has = (...allowed: string[]) => Boolean(actor?.grants.some(g => allowed.includes(g.role)));

  const load = useCallback(async (appendAfter?: string) => {
    if (!actor) return;
    const scope = ++dataScope.current;
    setLoading(true); setError("");
    const route: Record<Section, string> = { Facilities: "/facilities", Applications: "/applications", Organisation: "/organisation-units", Standards: "/criteria", Access: "/accounts", Audit: "/audit" };
    try {
      const [result, unitList, operatorList, criterionList] = await Promise.all([
        api<{items: Row[]; next_cursor?: string}>(route[section] + (appendAfter ? `?after=${encodeURIComponent(appendAfter)}` : "")),
        api<{items: Row[]}>("/organisation-units"), api<{items: Row[]}>("/operators"), api<{items: Row[]}>("/criteria"),
      ]);
      if (scope !== dataScope.current) return;
      setRows(old => appendAfter ? [...old, ...result.items] : result.items);
      setUnits(unitList.items); setOperators(operatorList.items); setCriteria(criterionList.items);
      setCursor(result.next_cursor || null);
      if (section === "Organisation") setResearch((await api<{items:Row[]}>("/organisation-research")).items);
      if (section === "Access") {setAccounts(result.items);setGrants((await api<{items:Row[]}>("/grants")).items);}
    } catch (e) {
      if (scope !== dataScope.current) return;
      if (e instanceof ApiFailure && e.status === 401) { setActor(null); setRows([]); setDossier(null); setSelected(null); }
      setError((e as Error).message);
    } finally { if (scope === dataScope.current) setLoading(false); }
  }, [actor, section]);
  useEffect(() => { setRows([]); setSelected(null); setDossier(null); void load(); }, [load]);

  async function mutate(path: string, body: unknown, form?: HTMLFormElement) {
    const encoded = JSON.stringify(body);
    const fingerprint = path + encoded;
    const key = pending.current.get(fingerprint) || crypto.randomUUID();
    pending.current.set(fingerprint, key);
    setBusy(true); setError(""); setSuccess("");
    try {
      const result = await api<{resource?: Row; status?: string}>(path, {method: "POST", headers: {"Content-Type": "application/json", "Idempotency-Key": key}, body: encoded});
      pending.current.delete(fingerprint);
      setSuccess(result.status ? human(result.status) : "Saved to the authoritative database.");
      form?.reset();
      await load();
      if (result.resource && selected?.id === result.resource.id) setSelected(result.resource);
      if (dossier && selected) await openApplication(result.resource?.id || selected.id);
      return result;
    } catch (e) { setError((e as Error).message); return null; }
    finally { setBusy(false); }
  }
  function submit(handler: (data: FormData, form: HTMLFormElement) => Promise<unknown>) {
    return (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const form = event.currentTarget;
      void handler(new FormData(form), form).catch(e => setError((e as Error).message));
    };
  }
  async function openApplication(id: string) {
    try {
      const result = await api<Record<string, unknown>>(`/applications/${id}`);
      setDossier(result); setSelected(result.application as Row);
      if (has("PLATFORM_ADMIN", "REGISTRY_STEWARD", "STANDARDS_REVIEWER")) setAccounts((await api<{items: Row[]}>("/accounts")).items);
    } catch (e) { setError((e as Error).message); }
  }

  if (checking) return <main id="main" className="auth"><p role="status">Checking your session…</p></main>;
  if (!actor) return <main id="main" className="auth"><div className="wordmark">LW <span>HEALTH INTELLIGENCE PLATFORM</span></div><div className="panel"><p className="eyebrow">HEALTH SERVICES DIRECTORATE</p><h1>Welcome back.</h1><p className="muted">Sign in to your authorised workspace.</p>{error && <p className="error" role="alert">{error}</p>}<form onSubmit={submit(async data => {
    setBusy(true); setError("");
    try { await api("/auth/login", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({email: get(data,"email"), password: String(data.get("password")), otp: get(data,"otp")})}); setActor(await api<Actor>("/auth/me")); }
    catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  })}><label>Work email<input type="email" name="email" autoComplete="username" required /></label><label>Password<input type="password" name="password" autoComplete="current-password" maxLength={256} required /></label><label>Authenticator code<input name="otp" inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" required /></label><button disabled={busy}>{busy ? "Verifying…" : "Sign in securely"}</button></form><p className="muted"><a href="/recover">Recover your account.</a> Access is invitation only. Contact your Directorate administrator if you need an account.</p></div><a href="/directory">Find a participating facility ↗</a></main>;

  const selectedFacility = selected && section === "Facilities" ? selected : null;
  const application = dossier?.application as Row | undefined;
  const requirementSet = dossier?.criteria as (Row & {requirements: {code:string;description:string;required:boolean}[]}) | undefined;
  const proofs = (dossier?.evidence || []) as Row[];
  const version = application?.version;
  const panel = (title: string, children: ReactNode) => <section className="panel"><h2>{title}</h2>{children}</section>;
  const scopeSummary = actor.grants.map(g => `${human(g.role)} · ${human(g.scope_type)}`).join(" / ");

  return <div className="workspace"><aside><div className="wordmark">LW <span>HEALTH INTELLIGENCE<br/>PLATFORM</span></div><p className="eyebrow">DIRECTORATE WORKSPACE</p><nav aria-label="Workspace">{sections.filter(s => s !== "Audit" || has("PLATFORM_ADMIN")).filter(s => s !== "Access" || has("PLATFORM_ADMIN")).map(s => <button key={s} aria-current={section === s ? "page" : undefined} onClick={() => {setSection(s);setSuccess("");}}>{s}</button>)}</nav><a href="/governance">Hierarchy, affiliation and editorial work</a><a href="/learn">Approved education and policy</a><a href="/operations">Account and operating controls &#8599;</a><a href="/directorate">Reporting and Directorate intelligence &#8599;</a><a href="/care">LW Care clinical workspace &#8599;</a><a href="/directory">Public facility directory ↗</a><div className="account"><strong>{actor.name}</strong><small>{scopeSummary}</small><button className="secondary" onClick={async () => {try {await api("/auth/logout",{method:"POST"});setActor(null);pending.current.clear();setRows([]);setSelected(null);setDossier(null);} catch(e){setError((e as Error).message);}}}>Sign out</button></div></aside><main id="main"><header><div><p className="eyebrow">HEALTH SERVICES DIRECTORATE</p><h1>{section === "Facilities" ? "A connected care network." : section}</h1><p className="muted">{section === "Facilities" ? "Register facilities, verify their identity and publish approved services." : "Act within your assigned authority. Every change retains its history."}</p></div><button className="secondary" disabled={loading} onClick={() => void load()}>{loading ? "Refreshing…" : "Refresh"}</button></header>
    {!online && <div className="error" role="status">This device is offline. Central changes cannot be confirmed until the connection returns. Your open form remains on this device.</div>}
    {error && <div className="error" role="alert">{error}</div>}{success && <div className="success" role="status">{success}</div>}
    <div className="content"><section className="panel"><div className="panel-heading"><h2>{section === "Facilities" ? "Facility registry" : section}</h2><span className="badge">{loading ? "Loading" : `${rows.length} loaded`}</span></div>{loading && !rows.length ? <p role="status">Loading records…</p> : !rows.length ? <div className="empty"><h3>No {section.toLowerCase()} recorded.</h3><p>The next authorised action is available below. Existing records will appear here after they are saved.</p></div> : <div className="table-wrap"><table><thead><tr>{(section === "Facilities" ? ["Facility", "Ownership", "Affiliation", "Publication", "Readiness", ""] : section === "Applications" ? ["Application", "State", "Version", ""] : section === "Audit" ? ["Action", "Outcome", "Recorded", "Resource"] : ["Name", "Details", "Reference"]).map((h,i) => <th key={i} scope="col">{h}</th>)}</tr></thead><tbody>{rows.map(r => <tr key={r.id}>{section === "Facilities" ? <><td><strong>{text(r,"name")}</strong><small>{text(r,"jurisdiction")} · {human(text(r,"site_type"))}</small></td><td>{human(text(r,"ownership"))}</td><td><span className="badge">{human(text(r,"affiliation_status"))}</span></td><td>{human(text(r,"publication_status"))}</td><td>{human(text(r,"readiness_status"))}</td><td><button className="secondary" onClick={() => {setSelected(r);setDossier(null);}}>Open</button></td></> : section === "Applications" ? <><td>{r.id}</td><td>{human(text(r,"state"))}</td><td>{text(r,"version")}</td><td><button className="secondary" onClick={() => void openApplication(r.id)}>Review</button></td></> : section === "Audit" ? <><td>{text(r,"action")}</td><td>{text(r,"outcome")}</td><td>{new Date(text(r,"recorded_at")).toLocaleString()}</td><td>{text(r,"resource_id")}</td></> : <><td>{text(r,"name")}</td><td>{text(r,section === "Organisation" ? "kind" : section === "Standards" ? "jurisdiction" : "email")}</td><td>{text(r,section === "Organisation" ? "code" : section === "Standards" ? "adoption_reference" : "active")}</td></>}</tr>)}</tbody></table></div>}{cursor && <button className="secondary" disabled={loading} onClick={() => void load(cursor)}>Load more</button>}</section>

    {section === "Facilities" && has("REGISTRY_STEWARD") && panel("Register a facility", <form onSubmit={submit((data,form) => mutate("/facilities", {
      operator_org_id:get(data,"operator"), zone_id:get(data,"zone"), site_name:get(data,"name"), site_type:get(data,"site_type"), ownership_category:get(data,"ownership"), jurisdiction_profile:get(data,"jurisdiction"), external_reference:get(data,"reference"), address:get(data,"address"), public_contact:get(data,"public_contact"), private_contact:get(data,"private_contact"), services:get(data,"services").split("\n").map(s=>s.trim()).filter(Boolean),
    },form))}><div className="form-grid"><Field name="name" label="Public facility name"/><Select name="operator" label="Operating organisation" rows={rowOptions(operators)}/><Select name="zone" label="Reporting zone" rows={rowOptions(units.filter(u=>u.kind === "ZONE"))}/><Select name="site_type" label="Facility type" rows={options(siteTypes)}/><Select name="ownership" label="Ownership" rows={options(["MINISTRY","MEMBER_OWNED","EXTERNAL"])}/><Field name="jurisdiction" label="Country or operating jurisdiction"/><Field name="reference" label="External registry reference (issuer and identifier)"/><Field name="address" label="Site address"/><Field name="public_contact" label="Approved public contact"/><Field name="private_contact" label="Private accountable contact"/></div><label>Declared services, one per line<textarea name="services" required rows={3}/></label><p className="muted">Registration records declared capability. Verification, affiliation, publication and current readiness are separate decisions.</p><button disabled={busy || !online}>Save facility</button></form>)}

    {selectedFacility && panel(text(selectedFacility,"name"), <><dl className="facts"><div><dt>Identity</dt><dd>{human(text(selectedFacility,"identity_status"))}</dd></div><div><dt>Statutory evidence</dt><dd>{human(text(selectedFacility,"statutory_status"))}</dd></div><div><dt>Version</dt><dd>{selectedFacility.version}</dd></div></dl>{has("REGISTRY_STEWARD") && <><h3>Verify registry information</h3><form onSubmit={submit(data=>mutate(`/facilities/${selectedFacility.id}/verification`,{expected_version:selectedFacility.version,identity_status:get(data,"identity"),statutory_status:get(data,"statutory"),reason:get(data,"reason")}))}><div className="form-grid"><Select name="identity" label="Identity finding" rows={options(["VERIFIED","DISPUTED"])}/><Select name="statutory" label="Statutory evidence finding" rows={options(["PENDING","CHECKED","EXPIRED","DISPUTED","NOT_APPLICABLE"])}/><Field name="reason" label="Verification evidence and reason"/></div><button disabled={busy}>Record verification</button></form><h3>Directory publication</h3><form onSubmit={submit(data=>mutate(`/facilities/${selectedFacility.id}/publication`,{expected_version:selectedFacility.version,action:get(data,"action"),reason:get(data,"reason")}))}><Select name="action" label="Publication action" rows={options(["PUBLISH","WITHDRAW"])}/><Field name="reason" label="Publication reason"/><button disabled={busy}>Record publication decision</button></form></>}<h3>Apply for affiliation</h3><form onSubmit={submit(data=>mutate("/applications",{facility_id:selectedFacility.id,criteria_id:get(data,"criteria")}))}><Select name="criteria" label="Adopted criterion set" rows={criteria.filter(r=>r.site_type === selectedFacility.site_type && r.jurisdiction === selectedFacility.jurisdiction).map(r=>({value:r.id,label:`${r.name} · ${text(r,"version")}`}))}/><button disabled={busy}>Create application</button></form></>)}

    {section === "Organisation" && panel("Region and zone source research",<><p className="muted">Partial public-source research. These findings have not been adopted into the Directorate register. Confirm parent relationships and effective dates before recording a unit.</p><div className="table-wrap"><table><thead><tr><th>Region</th><th>Zone</th><th>Evidence</th></tr></thead><tbody>{research.map(r=><tr key={r.id}><td>{text(r,"region")}</td><td>{text(r,"zone")}</td><td><a href={text(r,"source_url")} target="_blank" rel="noreferrer">{text(r,"source_title")}</a><small>{human(text(r,"evidence_status"))}</small><small>{text(r,"limitation")}</small></td></tr>)}</tbody></table></div></>)}
    {section === "Organisation" && has("PLATFORM_ADMIN") && panel("Add a ministry unit",<form onSubmit={submit((data,form)=>mutate("/organisation-units",{name:get(data,"name"),code:get(data,"code"),kind:get(data,"kind"),parent_id:get(data,"parent") || null,valid_from:date(data,"from"),valid_until:get(data,"until") ? date(data,"until") : null},form))}><div className="form-grid"><Field name="name" label="Official unit name"/><Field name="code" label="Registry unit code"/><Select name="kind" label="Unit type" rows={options(["REGION","ZONE"])}/><label>Parent region (required for zones)<select name="parent"><option value="">No parent — region only</option>{units.filter(r=>r.kind === "REGION").map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label><Field name="from" label="Effective from" type="datetime-local"/><Field name="until" label="Effective until (optional)" type="datetime-local" required={false}/></div><button disabled={busy}>Save unit</button></form>)}
    {section === "Organisation" && has("REGISTRY_STEWARD") && panel("Register an operating organisation",<form onSubmit={submit((data,form)=>mutate("/operators",{name:get(data,"name"),external_reference:get(data,"reference")},form))}><Field name="name" label="Registered organisation name"/><Field name="reference" label="Verified registration reference"/><button disabled={busy}>Save operating organisation</button></form>)}

    {section === "Standards" && has("STANDARDS_DECIDER") && panel("Record an adopted criterion set",<form onSubmit={submit((data,form)=>mutate("/criteria",{name:get(data,"name"),version:get(data,"version"),jurisdiction:get(data,"jurisdiction"),site_type:get(data,"site_type"),adoption_reference:get(data,"reference"),valid_from:date(data,"from"),valid_until:date(data,"until"),requirements:data.getAll("criterion_code").map((code,i)=>({code:String(code),description:String(data.getAll("criterion_description")[i]),required:data.getAll("criterion_required")[i] === "true"}))},form))}><div className="form-grid"><Field name="name" label="Criterion set name"/><Field name="version" label="Adopted version"/><Field name="jurisdiction" label="Country or operating jurisdiction"/><Select name="site_type" label="Applicable facility type" rows={options(siteTypes)}/><Field name="reference" label="Directorate adoption reference"/><Field name="from" label="Effective from" type="datetime-local"/><Field name="until" label="Expires at" type="datetime-local"/></div><h3>Evidence requirements</h3>{Array.from({length:criterionCount},(_,i)=><fieldset key={i}><legend>Criterion {i+1}</legend><div className="form-grid"><Field name="criterion_code" label="Criterion code"/><Field name="criterion_description" label="Evidence requirement"/><Select name="criterion_required" label="Requirement type" rows={[{value:"true",label:"Required"},{value:"false",label:"Improvement criterion"}]}/></div></fieldset>)}<button type="button" className="secondary" onClick={()=>setCriterionCount(n=>Math.min(n+1,100))}>Add criterion</button><p className="muted">Only enter criteria adopted by the authorised Directorate. Saved versions are immutable.</p><button disabled={busy}>Record adopted standard</button></form>)}

    {section === "Access" && has("PLATFORM_ADMIN") && panel("Invite a colleague or grant scoped access",<form onSubmit={submit((data,form)=>mutate("/invitations",{name:get(data,"name"),email:get(data,"email"),role:get(data,"role"),scope_type:get(data,"scope_type"),scope_id:get(data,"scope_id") || null,valid_until:date(data,"until")},form))}><div className="form-grid"><Field name="name" label="Full name"/><Field name="email" label="Work email" type="email"/><Select name="role" label="Role" rows={options(roles)}/><Select name="scope_type" label="Scope type" rows={options(["GLOBAL","REGION","ZONE","FACILITY"])}/><Field name="scope_id" label="Resource ID (leave empty for global scope)" required={false}/><Field name="until" label="Grant expires at" type="datetime-local"/></div><p className="muted">New accounts receive an enrolment invitation by email and must register an authenticator. Platform administration grants no clinical authority.</p><button disabled={busy}>Create invitation or grant</button></form>)}

    {section === "Access" && has("PLATFORM_ADMIN") && panel("Delegated authority",<div className="table-wrap"><table><thead><tr><th>Colleague</th><th>Role and scope</th><th>Validity</th><th>Action</th></tr></thead><tbody>{grants.map(g=><tr key={g.id}><td>{text(g,"name")}</td><td>{human(text(g,"role"))}<small>{human(text(g,"scope_type"))} ? {text(g,"scope_id")}</small></td><td>{g.revoked ? "Revoked" : new Date(text(g,"valid_until")).toLocaleString()}</td><td>{!g.revoked && g.account_id !== actor.id && <button className="secondary" disabled={busy} onClick={()=>void mutate(`/grants/${g.id}/revoke`,{})}>Revoke access</button>}</td></tr>)}</tbody></table></div>)}
    {section === "Applications" && application && panel("Affiliation review dossier",<><dl className="facts"><div><dt>State</dt><dd>{human(text(application,"state"))}</dd></div><div><dt>Facility</dt><dd>{text(dossier?.facility as Row,"name")}</dd></div><div><dt>Version</dt><dd>{version}</dd></div></dl><h3>Required evidence</h3><ul>{requirementSet?.requirements.map(r=><li key={r.code}><strong>{r.code}</strong> — {r.description}{r.required ? " (required)" : ""}</li>)}</ul>{proofs.length ? <ul>{proofs.map(r=><li key={r.id}><a href={`/v1/evidence/${r.id}/download`}>{text(r,"filename")}</a> · {text(r,"criterion")} · {human(text(r,"scan_status"))}</li>)}</ul> : <p className="muted">No evidence has been uploaded.</p>}
      {application.state === "DRAFT" && has("REGISTRY_STEWARD","FACILITY_ADMIN") && <><form onSubmit={submit(async (data,form)=>{
        const file=data.get("file") as File; const fingerprint=`evidence:${application.id}:${file.name}:${file.size}`; const key=pending.current.get(fingerprint) || crypto.randomUUID(); pending.current.set(fingerprint,key); setBusy(true);
        try {const query=new URLSearchParams({criterion:get(data,"criterion"),filename:file.name,source:get(data,"source"),expires_at:date(data,"until")});await api(`/applications/${application.id}/evidence?${query}`,{method:"POST",headers:{"Content-Type":file.type,"Idempotency-Key":key},body:file});pending.current.delete(fingerprint);form.reset();await openApplication(application.id);setSuccess("Evidence scanned and stored privately.");}catch(e){setError((e as Error).message);}finally{setBusy(false);}
      })}><Select name="criterion" label="Evidence criterion" rows={(requirementSet?.requirements || []).map(r=>({value:r.code,label:r.code}))}/><label>Original evidence document<input type="file" name="file" accept="application/pdf,image/png,image/jpeg" required/></label><Field name="source" label="Issuing source and verification reference"/><Field name="until" label="Evidence expiry" type="datetime-local"/><button disabled={busy}>Scan and upload evidence</button></form><button disabled={busy} onClick={()=>void mutate(`/applications/${application.id}/submit`,{expected_version:version})}>Submit application</button></>}
      {application.state === "SUBMITTED" && has("REGISTRY_STEWARD","STANDARDS_REVIEWER") && <form onSubmit={submit(data=>mutate(`/applications/${application.id}/assignment`,{expected_version:version,inspector_id:get(data,"inspector"),reviewer_id:get(data,"reviewer")}))}><Select name="inspector" label="Independent inspector" rows={rowOptions(accounts.filter(a=>a.active))}/><Select name="reviewer" label="Independent reviewer" rows={rowOptions(accounts.filter(a=>a.active))}/><button disabled={busy}>Assign inspection and review</button></form>}
      {application.state === "INSPECTION" && application.inspector_id === actor.id && <form onSubmit={submit(data=>mutate(`/applications/${application.id}/inspections`,{expected_version:version,conflict_declared:data.get("conflict") === "on",observed_at:date(data,"observed"),findings:(requirementSet?.requirements || []).map(r=>({criterion:r.code,observation:get(data,`observation_${r.code}`),outcome:get(data,`outcome_${r.code}`),evidence_ids:data.getAll(`evidence_${r.code}`).map(String)}))}))}><Field name="observed" label="Actual inspection time" type="datetime-local"/><label className="checkbox"><input type="checkbox" name="conflict"/>I have a conflict of interest and require reassignment</label>{requirementSet?.requirements.map(r=><fieldset key={r.code}><legend>{r.code} ? {r.description}</legend><label>Observed finding<textarea name={`observation_${r.code}`} required rows={3}/></label><Select name={`outcome_${r.code}`} label="Finding outcome" rows={options(["MET","NOT_MET","NOT_OBSERVED"])}/><label>Supporting evidence (select each applicable document)<select name={`evidence_${r.code}`} multiple required>{proofs.filter(p=>p.criterion===r.code).map(p=><option key={p.id} value={p.id}>{text(p,"filename")}</option>)}</select></label></fieldset>)}<button disabled={busy}>Attest inspection findings</button></form>}
      {application.state === "EVIDENCE_REVIEW" && application.reviewer_id === actor.id && <form onSubmit={submit(data=>mutate(`/applications/${application.id}/recommendation`,{expected_version:version,decision:get(data,"decision"),reason:get(data,"reason")}))}><Select name="decision" label="Recommendation" rows={options(["APPROVE","CONDITIONAL","REJECT"])}/><Field name="reason" label="Evidence-based recommendation reason"/><button disabled={busy}>Record recommendation</button></form>}
      {Boolean(application.recommendation) && <section><h3>Independent recommendation</h3><p>{human(String((application.recommendation as Record<string,unknown>).decision))}: {String((application.recommendation as Record<string,unknown>).reason)}</p></section>}
      {application.state === "RECOMMENDED" && has("STANDARDS_DECIDER") && <form onSubmit={submit(data=>mutate(`/applications/${application.id}/decisions`,{expected_version:version,decision:get(data,"decision"),reason:get(data,"reason"),scope:get(data,"scope"),conditions:get(data,"conditions"),effective_at:date(data,"from"),expires_at:date(data,"until"),intent_confirmed:data.get("intent") === "on"}))}><Select name="decision" label="Final Directorate decision" rows={options(["APPROVE","CONDITIONAL","REJECT"])}/><Field name="reason" label="Decision reasons and evidence"/><Field name="scope" label="Exact affiliation scope"/><Field name="conditions" label="Conditions (required for conditional recognition)" required={false}/><Field name="from" label="Effective from" type="datetime-local"/><Field name="until" label="Affiliation expires at" type="datetime-local"/><label className="checkbox"><input type="checkbox" name="intent" required/>I intend to record this final Directorate decision</label><button disabled={busy}>Record final decision</button></form>}
      {((dossier?.inspections || []) as Row[]).map(r=><details key={r.id}><summary>Attested inspection · {text(r,"recorded_at")}</summary><ul>{(r.findings as {criterion:string;outcome:string;observation:string}[]).map(f=><li key={f.criterion}><strong>{f.criterion} ? {human(f.outcome)}</strong><p>{f.observation}</p></li>)}</ul></details>)}{((dossier?.decisions || []) as Row[]).map(r=><details key={r.id} open><summary>Directorate decision · {human(text(r,"decision"))}</summary><p>{text(r,"reason")}</p><p>Scope: {text(r,"scope")}</p></details>)}
    </>)}
    {has("PLATFORM_ADMIN") && <IntegrationControls/>}</div><footer>LW Health Intelligence Platform · Health Services Directorate</footer></main></div>;
}
