type Declared = {definition_id:string;completeness:string;value:string;numerator:string;denominator:string;source_reference:string;explanation:string;extract_id?:string};
type Extracted = {value?:string|null;numerator?:string|null;denominator?:string|null;completeness?:string;explanation?:string};
export function applyExtract<T extends Declared>(values:T[],extract:{id:string;data:{values:Record<string,Extracted>}}):T[]{
 return values.map(value=>{
  const source=extract.data.values[value.definition_id];
  if(!source)return value;
  return {...value,completeness:source.completeness||"VALUE",value:source.value==null?"":String(source.value),numerator:source.numerator==null?"":String(source.numerator),denominator:source.denominator==null?"":String(source.denominator),explanation:source.explanation||"",source_reference:`Governed clinical extract ${extract.id}`,extract_id:extract.id};
 });
}
