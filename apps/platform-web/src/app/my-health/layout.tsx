import type {Metadata,Viewport} from "next";
import type {ReactNode} from "react";
import Install from "./install";

export const metadata:Metadata={title:"My LW Health Care",description:"Your verified personal and family care, reviewed information and care-team requests.",manifest:"/my-health.webmanifest",applicationName:"My LW Health Care",appleWebApp:{capable:true,title:"My LW Health",statusBarStyle:"default"},icons:{apple:"/health-icon-180.png",icon:"/health-icon-192.png"}};
export const viewport:Viewport={themeColor:"#0a574e"};
export default function PersonalLayout({children}:{children:ReactNode}){return <>{children}<Install/></>;}
