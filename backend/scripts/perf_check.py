import asyncio
import statistics
import time
from datetime import datetime
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.models.schemas import SlideVersion, SlideWithHistory, TemplateType, ToneType
from app.services.auth_service import create_access_token, hash_password
from app.services.ppt_service import ppt_service
from app.services.session_service import session_manager
from db import crud
from db.database import get_db_session, init_db


def timed_ms(fn):
    start = time.perf_counter()
    value = fn()
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, value


async def timed_ms_async(fn):
    start = time.perf_counter()
    value = await fn()
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, value


def avg(values):
    if not values:
        return 0.0
    return round(statistics.mean(values), 2)


async def ensure_bench_user():
    email = f"bench_{int(time.time())}@example.com"
    db = await get_db_session()
    try:
        user = await crud.create_user(
            db=db,
            name="Bench User",
            email=email,
            password_hash=hash_password("bench-pass-123"),
            provider="email",
        )
        return user
    finally:
        await db.close()


def build_sample_slides(count=8):
    slides = []
    for i in range(1, count + 1):
        ver = SlideVersion(
            version=0,
            title=f"Slide {i} Title",
            content=[
                f"Point A for slide {i}",
                f"Point B for slide {i}",
                f"Point C for slide {i}",
                f"Point D for slide {i}",
            ],
            speaker_notes=f"Notes for slide {i}",
            created_at=datetime.utcnow(),
            instruction="Initial generation",
        )
        slides.append(
            SlideWithHistory(
                slide_number=i,
                versions=[ver],
                current_version=0,
            )
        )
    return slides


async def run():
    await init_db()

    user = await ensure_bench_user()
    token = create_access_token(user.user_id, user.email, user.name)
    headers = {"Authorization": f"Bearer {token}"}

    transport = httpx.ASGITransport(app=app)

    api = {}
    db_stats = {}
    render = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # API: start session
        t_start, start_resp = await timed_ms_async(
            lambda: client.post(
                "/api/session/start",
                headers=headers,
                json={"template": "professional", "tone": "professional"},
            )
        )
        start_resp.raise_for_status()
        session_id = start_resp.json()["session_id"]
        api["session_start_ms"] = round(t_start, 2)

        # Seed slides so preview/download endpoints are meaningful.
        slides = build_sample_slides(10)
        await session_manager.update_session(
            session_id=session_id,
            topic="Benchmark deck",
            slides=slides,
            context_memory="benchmark",
            template=TemplateType.PROFESSIONAL,
            tone=ToneType.PROFESSIONAL,
        )
        updated = await session_manager.get_session(session_id)
        api["slides_after_seed"] = len(updated.slides) if updated else 0

        get_session_runs = []
        for _ in range(5):
            t, resp = await timed_ms_async(lambda: client.get(f"/api/session/{session_id}", headers=headers))
            resp.raise_for_status()
            get_session_runs.append(t)
        api["session_get_avg_ms"] = avg(get_session_runs)

        t_preview, preview_resp = await timed_ms_async(
            lambda: client.get(f"/api/preview/{session_id}", headers=headers)
        )
        api["preview_status"] = preview_resp.status_code
        api["preview_ms"] = round(t_preview, 2)

        t_template, template_resp = await timed_ms_async(
            lambda: client.post(
                f"/api/session/{session_id}/template",
                headers=headers,
                params={"template": "professional"},
            )
        )
        template_resp.raise_for_status()
        api["template_update_ms"] = round(t_template, 2)

        t_d1, d1 = await timed_ms_async(lambda: client.get(f"/api/download/{session_id}", headers=headers))
        api["download_first_status"] = d1.status_code
        api["download_first_ms"] = round(t_d1, 2)
        t_d2, d2 = await timed_ms_async(lambda: client.get(f"/api/download/{session_id}", headers=headers))
        api["download_second_status"] = d2.status_code
        api["download_second_ms"] = round(t_d2, 2)

        # DB checks: compare full eager load vs row-only query.
        db = await get_db_session()
        try:
            full_load = []
            row_only = []
            slide_fetch = []
            map_lookup = []
            for _ in range(15):
                t, _ = await timed_ms_async(lambda: crud.get_session_by_uuid(db, session_id))
                full_load.append(t)
                t, _ = await timed_ms_async(lambda: crud.get_session_row_by_uuid(db, session_id))
                row_only.append(t)
                t, _ = await timed_ms_async(lambda: crud.get_slide(db, session_id, 1))
                slide_fetch.append(t)
                t, _ = await timed_ms_async(lambda: crud.get_session_user_map(db, session_id))
                map_lookup.append(t)

            db_stats["session_full_load_avg_ms"] = avg(full_load)
            db_stats["session_row_only_avg_ms"] = avg(row_only)
            db_stats["slide_fetch_avg_ms"] = avg(slide_fetch)
            db_stats["session_owner_map_avg_ms"] = avg(map_lookup)

            t_inc, _ = await timed_ms_async(lambda: crud.increment_user_requests_by_id(db, user.id, amount=1))
            db_stats["increment_requests_by_id_ms"] = round(t_inc, 2)
        finally:
            await db.close()

        session = await session_manager.get_session(session_id)
        t_r1, path1 = timed_ms(lambda: ppt_service.create_presentation(session))
        t_r2, path2 = timed_ms(lambda: ppt_service.create_presentation(session))
        render["render_first_ms"] = round(t_r1, 2)
        render["render_second_ms"] = round(t_r2, 2)
        render["render_cache_hit"] = path1 == path2

    print("PERF_CHECK_RESULTS")
    print({
        "api": api,
        "db": db_stats,
        "render": render,
    })


if __name__ == "__main__":
    asyncio.run(run())
