const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {test}=require("node:test");
const ts=require("typescript");
const loaded={exports:{}};
new Function("exports","module",ts.transpileModule(fs.readFileSync(path.join(__dirname,"../src/app/directorate/extract-values.ts"),"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(loaded.exports,loaded);
const {applyExtract}=loaded.exports;
const draft=()=>({definition_id:"measure",completeness:"VALUE",value:"99",numerator:"99",denominator:"100",source_reference:"original manual source",explanation:"manual evidence"});
test("applying a native ratio retains actual components and partial source coverage",()=>{
 const original=draft(),result=applyExtract([original],{id:"extract",data:{values:{measure:{value:"50",numerator:"1",denominator:"2",completeness:"PARTIAL",explanation:"Native source only"}}}});
 assert.equal(result[0].numerator,"1");assert.equal(result[0].denominator,"2");assert.equal(result[0].completeness,"PARTIAL");assert.equal(result[0].extract_id,"extract");assert.equal(original.value,"99");
});
test("an unavailable source clears old numeric parts and never becomes a clinical zero",()=>{
 const [value]=applyExtract([draft()],{id:"extract",data:{values:{measure:{value:null,numerator:null,denominator:null,completeness:"UNKNOWN",explanation:"Denominator unavailable"}}}});
 assert.equal(value.value,"");assert.equal(value.numerator,"");assert.equal(value.denominator,"");assert.equal(value.completeness,"UNKNOWN");
});
test("unmapped manual values remain intact and legacy contact extracts remain usable",()=>{
 const original=draft();assert.equal(applyExtract([original],{id:"extract",data:{values:{}}})[0],original);
 const [value]=applyExtract([original],{id:"extract",data:{values:{measure:{value:"0"}}}});
 assert.equal(value.value,"0");assert.equal(value.completeness,"VALUE");assert.equal(value.denominator,"");
});
