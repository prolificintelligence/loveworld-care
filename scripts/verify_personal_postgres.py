"""Actual Phase 5 Neon proof in a disposable schema; no production seeding or messages."""

import asyncio
import json
import re
import sys
import traceback
from pathlib import Path

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
sys.path.insert(0, str(ROOT / "tests/integration"))
from lw_care_api.platform import db
from lw_care_api.platform.clinical import tables as t
from lw_care_api.platform.clinical.flow_index import index
from lw_care_api.platform.config import PlatformSettings
from lw_care_api.platform.main import create_platform_app
from test_platform_controls import ORIGIN, seed_controls, stamp


async def verify():
    cfg = PlatformSettings(_env_file=ROOT / ".env.platform.local")
    database = db.Database(cfg.database_url)
    namespace = "lwh_personal_verify_" + db.uid().replace("-", "")
    assert re.fullmatch(r"lwh_personal_verify_[0-9a-f]{32}", namespace)
    settings = cfg.model_copy(
        update={
            "environment": "test",
            "web_origin": ORIGIN,
            "dispatch_recovery_after_commit": False,
            "resend_api_key": "synthetic-not-a-sending-key",
            "enforce_activation_dossiers": False,
        }
    )
    app = create_platform_app(settings)
    await app.state.database.engine.dispose()
    mapped = database.engine.execution_options(schema_translate_map={db.SCHEMA: namespace})
    app.state.database.engine = mapped
    app.state.database.session = async_sessionmaker(mapped, expire_on_commit=False)
    try:
        assert await database.version() in {7, 8}
        async with database.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            translated = await connection.execution_options(
                schema_translate_map={db.SCHEMA: namespace}
            )
            await translated.run_sync(db.metadata.create_all)
            await db.protect_history(translated, namespace, schema_version=8)
        async with app.state.database.transaction() as session:
            await session.execute(
                db.schema_versions.insert().values(version=8, applied_at=db.now())
            )
        actors, facility = await seed_controls(app)
        from lw_care_api.platform.personal import tables as personal
        from lw_care_api.platform.security import issue_session
        async with app.state.database.transaction() as session:
            await session.execute(update(t.privileges).where(t.privileges.c.account_id.in_([actors["target"][0],actors["successor"][0]])).values(capabilities=["REGISTER","CARE","RECORDS"]))
            person=db.uid()
            await session.execute(db.accounts.insert().values(id=person,email="personal@synthetic.invalid",name="Synthetic personal verifier",active=True,totp_last_step=-1,created_at=db.now()))
            token=await issue_session(session,person,30)
            actors["person"]=(person,token)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN) as client:
            async def post(path,body,actor="target",key=None):
                return await client.post("/v1"+path,json=body,headers={"Origin":ORIGIN,"Authorization":"Bearer "+actors[actor][1],"Idempotency-Key":key or db.uid()})
            async def create(path,body,actor="target"):
                response=await post(path,body,actor)
                assert response.status_code==200,(path,response.status_code,response.json().get("error",{}).get("code"))
                return response.json()["resource"]
            prefix="/clinical/"+facility
            patient=await create(prefix+"/patients",{"display_name":"Synthetic personal patient","provisional":False,"sex":"UNKNOWN","identity_evidence":"Synthetic independently confirmed identity"})
            encounter=await create(prefix+"/encounters",{"patient_id":patient["id"],"service":"GENERAL","encounter_type":"AMBULATORY","arrival":"WALK_IN","complaint":"Synthetic proof only","occurred_at":stamp(-1)})
            encounter=await create(prefix+"/encounters/"+encounter["id"]+"/accept",{"patient_id":patient["id"],"expected_version":encounter["version"],"reason":"Synthetic personal clinical acceptance","intent_confirmed":True})
            note=await create(prefix+"/notes",{"patient_id":patient["id"],"encounter_id":encounter["id"],"occurred_at":stamp(-1),"note_type":"CONSULTATION","narrative":"Synthetic private clinical source","source":"Synthetic verifier"})
            note=await create(prefix+"/notes/"+note["id"]+"/sign",{"patient_id":patient["id"],"expected_version":1,"reason":"Synthetic signing intent","intent_confirmed":True})
            link=await create("/personal/links",{"facility_id":facility,"relationship":"SELF","patient_reference":"Synthetic registration reference","relationship_basis":"Synthetic verified personal identity"},"person")
            link=await create("/personal/staff/links/"+link["id"]+"/review",{"expected_version":1,"decision":"APPROVE","patient_id":patient["id"],"expected_patient_version":1,"permissions":["READ","REQUEST"],"valid_until":stamp(3),"review_at":stamp(2),"authority_type":"SYNTHETIC_ONLY","evidence_examined":"Synthetic independently examined evidence","policy_reference":"Synthetic policy only","reason":"Synthetic independent decision","intent_confirmed":True},"successor")
            await create("/personal/staff/links/"+link["id"]+"/releases",{"source_id":note["id"],"expected_source_version":note["version"],"kind":"PLAN","title":"Synthetic reviewed plan","readable_text":"Synthetic patient-readable information","release_basis":"Synthetic actual review","intent_confirmed":True})
            response=await client.get("/v1/personal/links/"+link["id"]+"/care",headers={"Authorization":"Bearer "+token})
            assert response.status_code==200 and len(response.json()["items"])==1 and "private clinical source" not in response.text
            service=await create("/personal/staff/"+facility+"/services",{"name":"Synthetic receiving service","primary_id":actors["target"][0],"fallback_id":actors["successor"][0],"response_minutes":60,"valid_until":stamp(2),"policy_reference":"Synthetic actual service commitment","intent_confirmed":True},"proposer")
            for actor in ("target","successor"):
                service=await create("/personal/staff/services/"+service["id"]+"/actions",{"expected_version":service["version"],"action":"ACCEPT_DUTY","reason":"Synthetic personal duty acceptance"},actor)
            key=db.uid();body={"service_id":service["id"],"kind":"CARE","text":"Synthetic patient care request"};path="/personal/links/"+link["id"]+"/requests"
            results=await asyncio.gather(post(path,body,"person",key),post(path,body,"person",key))
            assert all(r.status_code==200 for r in results) and results[0].json()==results[1].json()
            request=results[0].json()["resource"]
            request=await create("/personal/staff/requests/"+request["id"]+"/actions",{"expected_version":request["version"],"action":"ACCEPT","reason":"Synthetic actual acceptance"})
            await create("/personal/links/"+link["id"]+"/revoke",{"expected_version":link["version"],"reason":"Synthetic personal withdrawal"},"person")
            denied=await post(path,body,"person",key)
            assert denied.status_code==403
            response=await client.get("/v1/personal/staff/requests/"+request["id"],headers={"Authorization":"Bearer "+actors["target"][1]})
            assert response.status_code==200
        blocked=False
        try:
            async with app.state.database.transaction() as session:
                await session.execute(personal.events.delete())
        except DBAPIError:
            blocked=True
        assert blocked
        print(json.dumps({"personal_postgres":"PASSED","schema_version":8,"concurrent_duplicate_requests":"ONE_COMMITTED_RECEIPT","revoked_access_replay":"DENIED","accepted_responsibility_preserved":True,"raw_clinical_source_withheld":True,"history_mutation":"REJECTED","production_patient_records_seeded":0}),flush=True)
    finally:
        assert re.fullmatch(r"lwh_personal_verify_[0-9a-f]{32}", namespace) and namespace != db.SCHEMA
        async with database.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
        await database.engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as exc:  # noqa: BLE001 -- never render secrets, source records or provider bodies
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        print(
            json.dumps(
                {
                    "phase5_postgres_verification": "FAILED",
                    "error_type": type(exc).__name__,
                    "source": Path(frame.filename).name,
                    "line": frame.lineno,
                    "sqlstate": getattr(getattr(exc, "orig", None), "sqlstate", None),
                }
            )
        )
        raise SystemExit(1) from None
