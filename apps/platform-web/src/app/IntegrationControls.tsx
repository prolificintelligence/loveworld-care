"use client";

import { useState } from "react";
import { api } from "./api";

type Status = {openrouter:{model:string;ai_enabled:boolean};upstash:{reachable:boolean};email:{configured:boolean}};

export default function IntegrationControls() {
  const [status,setStatus]=useState<Status|null>(null);
  const [message,setMessage]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function execute(path?:string,body?:unknown) {
    setBusy(true);setError("");setMessage("");
    try {
      if(path){const result=await api<{status?:string;model?:string;provider_accepted?:number;retry_pending?:number}>(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body || {})});setMessage(result.status ? `${result.status.replaceAll("_"," ")}${result.model ? ` · ${result.model}` : ""}` : `Provider accepted: ${result.provider_accepted || 0}; retry pending: ${result.retry_pending || 0}`);}
      setStatus(await api<Status>("/integrations"));
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <section className="panel"><h2>Cloud integration controls</h2><p className="muted">Verify the configured free model with fixed public readiness text. This check transmits no patient data and does not enable clinical AI workflows.</p>{error && <p role="alert" className="error">{error}</p>}{message && <p role="status" className="success">{message}</p>}{status && <dl className="facts"><div><dt>Free model</dt><dd>{status.openrouter.model || "Not configured"}</dd></div><div><dt>AI probe control</dt><dd>{status.openrouter.ai_enabled ? "Enabled" : "Disabled"}</dd></div><div><dt>Shared control store</dt><dd>{status.upstash.reachable ? "Reachable" : "Unavailable"}</dd></div><div><dt>Invitation email</dt><dd>{status.email.configured ? "Configured" : "Unavailable"}</dd></div></dl>}<div className="actions"><button className="secondary" disabled={busy} onClick={()=>void execute()}>Check connections</button><button disabled={busy} onClick={()=>void execute("/integrations/openrouter/verify")}>Verify free model</button><button className="secondary" disabled={busy} onClick={()=>void execute("/integrations/ai-control",{enabled:!status?.openrouter.ai_enabled})}>{status?.openrouter.ai_enabled ? "Disable AI probes" : "Enable AI probes"}</button><button className="secondary" disabled={busy} onClick={()=>void execute("/invitations/deliver")}>Retry invitation delivery</button></div></section>;
}
