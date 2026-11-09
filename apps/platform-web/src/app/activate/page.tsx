"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";

export default function Activate() {
  const [destination,setDestination]=useState("/");
  const [token,setToken]=useState("");
  const [setup,setSetup]=useState<{setup_key:string;authenticator_uri:string}|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  useEffect(()=>{setDestination(new URLSearchParams(window.location.search).get("next")==="my-health"?"/my-health":"/");setToken(window.location.hash.slice(1));history.replaceState(null,"","/activate");},[]);
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data=new FormData(event.currentTarget); setBusy(true);setError("");
    try {
      if(!setup) {
        const password=String(data.get("password"));
        if(password!==data.get("confirm")) throw new Error("The passwords do not match.");
        setSetup(await api("/auth/enrol",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token,password})}));
      } else {
        await api("/auth/activate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token,otp:String(data.get("otp"))})});
        setToken("");setSetup(null);window.location.assign(destination);
      }
    } catch(e){setError((e as Error).message);} finally{setBusy(false);}
  }
  return <main id="main" className="auth"><div className="wordmark">LW <span>HEALTH INTELLIGENCE PLATFORM</span></div><section className="panel"><p className="eyebrow">YOUR PRIVATE ACCOUNT LINK</p><h1>{setup ? "Secure your account." : "Activate your account."}</h1>{!token && <p role="alert" className="error">Open the complete private link in your invitation email. Contact your administrator if it has expired.</p>}{error && <p className="error" role="alert">{error}</p>}<form onSubmit={submit}>{setup ? <><p>In your authenticator app, add a time-based account named “LW Health Intelligence Platform” and enter this setup key. Keep it private.</p><code className="setup-key">{setup.setup_key}</code><label>Current six-digit authenticator code<input name="otp" inputMode="numeric" pattern="[0-9]{6}" autoComplete="one-time-code" required/></label></> : <><p>Choose a unique password with at least 14 characters. You will then register your authenticator.</p><label>New password<input name="password" type="password" minLength={14} maxLength={256} autoComplete="new-password" required/></label><label>Confirm password<input name="confirm" type="password" minLength={14} maxLength={256} autoComplete="new-password" required/></label></>}<button disabled={!token || busy}>{busy ? "Verifying…" : setup ? "Activate and sign in" : "Continue to authenticator setup"}</button></form></section><a href="/">Back to sign in</a></main>;
}
