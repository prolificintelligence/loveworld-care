"""Validate documentation and capture contracts; does not test a clinical platform.

Run with Python plus PyYAML, jsonschema and referencing installed. No network,
production data, model calls or platform mutations are performed.
"""
from pathlib import Path
import json, re, hashlib, copy, sys
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT=Path(__file__).resolve().parents[1]
failures=[];checks=0
def check(ok,message):
 global checks
 checks+=1
 if not ok:failures.append(message)

manifest=json.loads((ROOT/'manifest.json').read_text())
docs=manifest['documents'];ids={d['document_id'] for d in docs}
check(len(docs)==78 and len(ids)==78,'Expected 78 unique controlled documents')
check(len([d for d in docs if d['document_id'].startswith('LWH-PRD-')])==25,'Expected 25 PRDs')
check(len([d for d in docs if d['document_id'].startswith('LWH-SPEC-')])==21,'Expected 21 shared specifications')
source_data=json.loads((ROOT/'contracts/source_register.json').read_text())
source_ids={s['id'] for s in source_data}|{f'PROJECT-{i:03}' for i in range(1,5)}
check(len(source_data)==51,'Expected 51 external references')
texts={}
for d in docs:
 p=ROOT/d['path'];check(p.is_file(),f'Missing document {d["path"]}')
 if not p.is_file():continue
 t=p.read_text();texts[d['document_id']]=t
 check(t.startswith('---\n'),f'Front matter missing: {p.name}')
 try:meta=yaml.safe_load(t.split('---\n',2)[1])
 except Exception as e:failures.append(f'Front matter parse {p.name}: {e}');continue
 check(meta.get('document_id')==d['document_id'],f'ID mismatch {p.name}')
 check(meta.get('document_status')=='authored_design_baseline',f'Unexpected status {p.name}')
 check(len(t.split())>=350,f'Document lacks expected substantive length: {p.name}')
 check(hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256'],f'Hash mismatch {p.name}')
 check(len(re.findall(r'^```',t,re.M))%2==0,f'Unbalanced code fence {p.name}')
 check('OUTLINE_ONLY' not in t,f'Stale outline-only status {p.name}')
 for ref in meta.get('depends_on',[]):check(ref in ids,f'Unknown dependency {ref} in {p.name}')
 for ref in meta.get('source_refs',[]):check(ref in source_ids,f'Unknown source {ref} in {p.name}')
 for ref in set(re.findall(r'\bLWH-(?:DOC|STR|DIR|BRD|ARC|STD|GOV|PRD|SPEC|ENG|OPS|COM)-\d{3}\b',t)):
  check(ref in ids,f'Unresolved document reference {ref} in {p.name}')
 for ref in set(re.findall(r'\bLWH-SRC-\d{3}\b',t)):check(ref in source_ids,f'Unresolved source {ref} in {p.name}')

requirements=json.loads((ROOT/'contracts/requirements.json').read_text())
cases=json.loads((ROOT/'contracts/acceptance_cases.json').read_text())
check(len(requirements)==200 and len({r['id'] for r in requirements})==200,'Requirement count/uniqueness')
check(len(cases)==111 and len({r['id'] for r in cases})==111,'Acceptance case count/uniqueness')
for r in requirements:check(r['id'] in texts[r['document_id']],f'Requirement absent from document {r["id"]}')
for c in cases:
 check(c['id'] in texts[c['document_id']],f'Acceptance absent from document {c["id"]}')
 check(c['execution_status']=='NOT_RUN',f'Implementation test result invented {c["id"]}')
trace=json.loads((ROOT/'contracts/directive_traceability.json').read_text())
check({x['id'] for x in trace}=={f'DHS-REQ-{i:03}' for i in range(1,21)},'All 20 directives must be traced')
case_ids={c['id'] for c in cases}
for row in trace:
 check(row['primary_document'] in ids,f'Directive owner missing {row["id"]}')
 for c in row['uat_cases']:check(c in case_ids,f'Directive case missing {c}')

fields=json.loads((ROOT/'contracts/form_field_manifest.json').read_text())
check(len(fields)==355 and len({f['id'] for f in fields})==355,'Field count/uniqueness')
for f in fields:
 check(f['id'] in texts['LWH-SPEC-006'],f'Field not documented {f["id"]}')
 check(f['source'] in source_ids,f'Field source unresolved {f["id"]}')

schemas=[json.loads(p.read_text()) for p in sorted((ROOT/'contracts/forms').glob('*.schema.json'))]
commands=json.loads((ROOT/'contracts/command_schemas.json').read_text())
check(len(schemas)==52 and len(commands)==15,'Schema catalogue counts')
all_schemas=schemas+commands
registry=Registry().with_resources([(s['$id'],Resource.from_contents(s)) for s in all_schemas])
structural_tests=0
for s in all_schemas:
 try:Draft202012Validator.check_schema(s);check(True,'schema valid')
 except Exception as e:check(False,f'Schema compile {s.get("$id")}: {e}')

uuid='00000000-0000-4000-8000-000000000001'
for s in schemas:
 if not s.get('title'):continue
 fid=s['properties']['form_id']['const'];v=Draft202012Validator(s,registry=registry,format_checker=FormatChecker())
 sample={'form_id':fid,'schema_version':'1.0.0','stage':'draft','authority_node_id':uuid,'actor_id':uuid,'facility_or_unit_id':uuid,'answers':{}}
 check(v.is_valid(sample),f'Valid minimal draft rejected {fid}');structural_tests+=1
 sample['stage']='submitted'
 for k in s['allOf'][0]['then']['properties']['answers']['required']:sample['answers'][k]={'absent_reason':'unknown'}
 if 'patient_id' in s['properties']:sample['patient_id']=uuid
 check(v.is_valid(sample),f'Explicit-unknown capture rejected {fid}');structural_tests+=1
 bad=copy.deepcopy(sample);bad['undeclared_field']='blocked'
 check(not v.is_valid(bad),f'Unknown root field allowed {fid}');structural_tests+=1
 bad=copy.deepcopy(sample);bad['actor_id']='not-a-uuid'
 check(not v.is_valid(bad),f'Invalid actor UUID accepted {fid}');structural_tests+=1
 bad=copy.deepcopy(sample);key=s['allOf'][0]['then']['properties']['answers']['required'][0];bad['answers'].pop(key)
 check(not v.is_valid(bad),f'Missing submitted field allowed {fid}.{key}');structural_tests+=1
 if 'patient_id' not in s['properties']:
  bad=copy.deepcopy(sample);bad['patient_id']=uuid
  check(not v.is_valid(bad),f'Institutional form permits patient key {fid}');structural_tests+=1

for s in commands:
 v=Draft202012Validator(s,format_checker=FormatChecker())
 base={'command_name':s['title'],'resource_id':uuid,'expected_version':1,'idempotency_key':'synthetic-key-0001','intent_confirmed':True,'reason':'Synthetic structural check','evidence_refs':['synthetic-evidence']}
 if 'decision' in s['properties']:base['decision']='approve'
 if 'receiving_team_id' in s['properties']:base['receiving_team_id']=uuid
 if 'independent_approval_ref' in s['properties']:base['independent_approval_ref']=uuid
 if 'allocation_request' in s['properties']:base['allocation_request']={'allocation_id':uuid,'kind':'service_units','amount':1}
 # Optional generic fields remain valid only when defined in this typed command.
 check(v.is_valid(base),f'Valid command structure rejected {s["title"]}');structural_tests+=1
 bad=copy.deepcopy(base);bad['intent_confirmed']=False
 check(not v.is_valid(bad),f'False intent allowed {s["title"]}');structural_tests+=1

common=next(s for s in schemas if '$defs' in s)
qv=Draft202012Validator({'$schema':'https://json-schema.org/draft/2020-12/schema','$ref':common['$id']+'#/$defs/quantity'},registry=registry)
check(not qv.is_valid({'value':'1'}),'Quantity accepted without unit');structural_tests+=1
check(not qv.is_valid({'value':'12mg','unit':{'system':'urn:synthetic','code':'unit'}}),'Quantity accepted mixed text value');structural_tests+=1
check(qv.is_valid({'value':'1','unit':{'system':'urn:synthetic','code':'unit'}}),'Exact quantity structure rejected');structural_tests+=1

api=json.loads((ROOT/'contracts/openapi.capture.json').read_text())
check(len(api['paths'])==52,'Capture route count')
for path,methods in api['paths'].items():
 for method,op in methods.items():
  check((ROOT/'contracts'/op['requestBody']['content']['application/json']['schema']['$ref']).is_file(),f'OpenAPI form ref missing {path}')
  names={p['name'] for p in op['parameters'] if p['in']=='path' and p['required']}
  check(set(re.findall(r'{([^}]+)}',path))==names,f'OpenAPI path parameters {path}')
queries=json.loads((ROOT/'contracts/query_catalogue.json').read_text());check(len(queries)==15,'Query catalogue count')
for p in ROOT.rglob('*.json'):
 try:json.loads(p.read_text());check(True,'JSON parsed')
 except Exception as e:check(False,f'Invalid JSON {p}: {e}')

all_text='\n'.join(texts.values())
check(len(set(re.findall(r'\bLWH-SCR-\d{3}\b',all_text)))==75,'Screen identity count')
check(len(set(re.findall(r'\bLWH-JRN-\d{3}\b',all_text)))==20,'Journey identity count')
check(len(set(re.findall(r'\bLWH-MET-\d{3}\b',all_text)))==45,'Metric identity count')
check(len(set(re.findall(r'\bLWH-STM-\d{3}\b',all_text)))==30,'State-family identity count')
check(len(set(re.findall(r'\bLWH-EVT-\d{3}\b',all_text)))==35,'Event identity count')
for p in ROOT.rglob('*.md'):
 for dest in re.findall(r'\[[^\]]+\]\(([^)]+)\)',p.read_text()):
  if '://' in dest or dest.startswith('#') or dest.startswith('sandbox:'):continue
  target=(p.parent/dest.split('#')[0]).resolve()
  check(target.exists(),f'Broken local link {p.name} -> {dest}')
check(30000//20==1500 and 30000//30==1000 and 30000//40==750,'Economic sensitivity arithmetic')

report={'suite_id':manifest['suite_id'],'issued':'2026-11-05','status':'PASSED' if not failures else 'FAILED','checks':checks,'failures':failures,'controlled_documents':len(docs),'controlled_document_words':sum(d['word_count'] for d in docs),'form_count':51,'tagged_fields':len(fields),'compiled_schemas':len(all_schemas),'synthetic_structural_examples':structural_tests,'specified_implementation_cases':len(cases),'implementation_cases_executed':0,'clinical_approval_claimed':False,'current_repository_or_production_verified':False}
(ROOT/'contracts/document_validation.json').write_text(json.dumps(report,indent=2))
text=f'''# Documentation validation report

Issued 5 November 2026. Status: **{report['status']}**.

- Controlled authored documents: {len(docs)}; controlled-document word count: {report['controlled_document_words']:,} (includes tables, identifiers and metadata).
- PRDs: 25; shared specifications: 21; recording-derived requirements traced: 20.
- Forms: 51; tagged fields: {len(fields)}; structurally compiled shared/form/command schemas: {len(all_schemas)}.
- Synthetic positive/negative structural examples: {structural_tests}; document/contract assertions: {checks}.
- Specified implementation acceptance cases: {len(cases)}; implementation cases executed: **0**.

Checks cover unique IDs/paths, metadata, dependencies/source references, content hashes, Markdown fences/links, directive and requirement/case presence, schema references/compilation, capture draft/unknown/required-field/format/privacy boundaries, command intent, exact quantity structure, OpenAPI reference/path consistency, catalogue counts, JSON syntax and illustrative arithmetic.

Structural capture examples use synthetic identifiers and explicit unknowns. They do not establish clinically complete data or permission to execute a consequential action. Clinical policy, professional authority, chronology, real terminology/units, state/business rules, persistence/concurrency, offline runtime, integrations, security, finance and operational readiness require the implementation tests and qualified review in the suite.

No live application, current repository, patient workflow, clinical protocol, legal compliance, source licence or operational service is certified by this report. Source review depth and outstanding institutional/country adoption are recorded in LWH-STD-001 and LWH-DIR-001. The supplied acceptance cases remain NOT_RUN until real evidence exists.

## Failures

'''+ ('None.\n' if not failures else '\n'.join('- '+x for x in failures)+'\n')
(ROOT/'VALIDATION_REPORT.md').write_text(text)
print(json.dumps(report,indent=2))
sys.exit(1 if failures else 0)
