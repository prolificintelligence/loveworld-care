"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, human, text, type Row } from "../api";

export default function Directory() {
  const [rows,setRows]=useState<Row[]>([]);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  const [cursor,setCursor]=useState<string|null>(null);
  const [query,setQuery]=useState("");
  async function load(search:string,after?:string) {
    setLoading(true);setError("");
    try {const data=await api<{items:Row[];next_cursor:string|null}>(`/directory?${search}${after ? `&after=${encodeURIComponent(after)}` : ""}`);setRows(previous=>after ? [...previous,...data.items] : data.items);setCursor(data.next_cursor);}
    catch(e){setError((e as Error).message);}finally{setLoading(false);}
  }
  useEffect(()=>{void load("");},[]);
  function search(event:FormEvent<HTMLFormElement>){event.preventDefault();const data=new FormData(event.currentTarget);const value=new URLSearchParams({jurisdiction:String(data.get("jurisdiction")||"").trim(),service:String(data.get("service")||"").trim()}).toString();setQuery(value);void load(value);}
  return <main id="main" className="directory"><header><a className="wordmark" href="/">LW <span>HEALTH INTELLIGENCE PLATFORM</span></a><a href="/">Staff sign in ↗</a></header><p className="eyebrow">FIND PARTICIPATING CARE</p><h1>Care starts with the right connection.</h1><p className="intro">Find facilities with current Directorate network affiliation. Affiliation describes ministry recognition; statutory licensing and live service availability are separate.</p><section className="panel"><form className="search" onSubmit={search}><label>Jurisdiction<input name="jurisdiction"/></label><label>Declared service<input name="service"/></label><button disabled={loading}>Search facilities</button></form></section>{error && <p className="error" role="alert">{error}</p>}{loading && <p role="status">Checking current directory records…</p>}{!loading && !error && !rows.length && <section className="panel empty"><h2>No published facilities match.</h2><p>Try another jurisdiction or service. Facilities appear only after verification, Directorate affiliation and an authorised publication decision.</p></section>}<div className="directory-grid">{rows.map(row=><article key={row.id} className="panel"><span className="badge">{human(text(row,"ownership"))}</span><h2>{text(row,"name")}</h2><p>{text(row,"address")}</p><p>{human(text(row,"site_type"))} · {text(row,"jurisdiction")}</p><h3>Declared services</h3><ul>{(row.services as string[]).map(service=><li key={service}>{service}</li>)}</ul><dl><dt>Affiliation</dt><dd>{human(text(row,"affiliation_status"))}</dd><dt>Scope</dt><dd>{text(row,"affiliation_scope")}</dd><dt>Conditions</dt><dd>{text(row,"conditions") || "None recorded"}</dd><dt>Current readiness</dt><dd>{human(text(row,"readiness_status"))} — contact the facility to confirm suitability and acceptance.</dd></dl><p><strong>Public contact</strong><br/>{text(row,"public_contact")}</p><small>Last registry update: {new Date(text(row,"updated_at")).toLocaleString()}</small></article>)}</div>{cursor && <button disabled={loading} onClick={()=>void load(query,cursor)}>Load more facilities</button>}<footer>LW Health Intelligence Platform · Health Services Directorate</footer></main>;
}
