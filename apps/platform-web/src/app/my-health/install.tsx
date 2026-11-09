"use client";
import {useEffect,useState} from "react";
type InstallPrompt=Event&{prompt:()=>Promise<void>;userChoice:Promise<{outcome:string}>};
export default function Install(){
 const [prompt,setPrompt]=useState<InstallPrompt|null>(null),[installed,setInstalled]=useState(false),[message,setMessage]=useState("");
 useEffect(()=>{setInstalled(window.matchMedia("(display-mode: standalone)").matches||Boolean((navigator as Navigator&{standalone?:boolean}).standalone));
  const available=(event:Event)=>{event.preventDefault();setPrompt(event as InstallPrompt);};const complete=()=>{setInstalled(true);setPrompt(null);};
  window.addEventListener("beforeinstallprompt",available);window.addEventListener("appinstalled",complete);
  if("serviceWorker" in navigator)void navigator.serviceWorker.register("/my-health-sw.js",{scope:"/my-health"}).catch(()=>setMessage("Installation support could not be prepared. You can continue securely in this browser."));
  return()=>{window.removeEventListener("beforeinstallprompt",available);window.removeEventListener("appinstalled",complete);};
 },[]);
 if(installed)return null;
 return <aside className="personal-shell" aria-label="Install personal care app"><section className="panel"><h2>Keep My LW Health Care close</h2><p>Install your personal care app for its own launch icon. A connection is required to read protected care information or send requests.</p>{prompt?<button onClick={async()=>{try{await prompt.prompt();const choice=await prompt.userChoice;setPrompt(null);setMessage(choice.outcome==="accepted"?"Installation requested. Open the app from your device when installation finishes.":"You can continue in this browser and install later.");}catch{setMessage("Use your browser’s install or Add to Home Screen option.");}}}>Install My LW Health Care</button>:<p>Use your browser’s Install app or Add to Home Screen option. On iPhone or iPad, open this page in Safari, then choose Share → Add to Home Screen.</p>}{message&&<p role="status">{message}</p>}</section></aside>;
}
