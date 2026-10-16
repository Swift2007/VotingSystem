"""Application entry point.

`create_app(settings)` builds the FastAPI app:
* configures the database and creates tables + append-only triggers,
* builds the ChainService (simulated network of nodes) and ballot key store,
* restores the mempool from any ballots not yet sealed (restart safety),
* cross-checks the database chain copy against the nodes and logs problems,
* starts the background loop that
    - seals due blocks (BLOCK_SIZE reached or BLOCK_INTERVAL_SECONDS passed), and
    - automatically closes + tallies elections whose closing time has passed
      (README: "When the election closes, votes are counted automatically").
      Publishing results stays a manual election-admin action.

Run:  cd backend && uvicorn app.main:app --reload
"""
import asyncio
import contextlib
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app import database
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chain import router as chain_router
from app.api.elections import router as elections_router
from app.api.receipts import router as receipts_router
from app.blockchain.service import ChainService
from app.config import Settings, settings as default_settings
from app.core.audit import audit
from app.core.ratelimit import RateLimiter
from app.core.timeutil import utcnow
from app.crypto.ballot import ElectionKeyStore
from app.models import Election
from app.services.errors import ServiceError

log = logging.getLogger("app")

_FINALIZE_RETRY_SECONDS = 30.0


def auto_finalize(chain: ChainService, keys: ElectionKeyStore, last_attempt: dict[int, float]) -> None:
    """Close and tally every election whose closing time has passed (one tick)."""
    from app.services.tally import run_tally

    with database.SessionLocal() as db:
        due = list(db.scalars(
            select(Election.id).where(Election.closes_at <= utcnow(), Election.tallied_at.is_(None))
        ))
        db.rollback()
    for election_id in due:
        if time.monotonic() - last_attempt.get(election_id, 0.0) < _FINALIZE_RETRY_SECONDS:
            continue
        last_attempt[election_id] = time.monotonic()
        with database.SessionLocal() as db:
            try:
                run_tally(db, chain, keys, None, election_id)
                log.info("election %s closed and tallied automatically", election_id)
            except Exception as error:  # surfaced in the audit log; retried later
                db.rollback()
                log.error("auto-tally of election %s failed: %s", election_id, error)
                audit(db, None, "auto_tally_failed", election_id=election_id, reason=str(error)[:300])
                db.commit()


async def background_loop(app: FastAPI) -> None:
    chain: ChainService = app.state.chain
    keys: ElectionKeyStore = app.state.keys
    last_attempt: dict[int, float] = {}
    while True:
        try:
            await asyncio.to_thread(chain.seal_due, database.SessionLocal)
            await asyncio.to_thread(auto_finalize, chain, keys, last_attempt)
        except Exception:  # never let the loop die
            log.exception("background loop error")
        await asyncio.sleep(app.state.settings.sealer_tick_seconds)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with database.SessionLocal() as db:
            restored = app.state.chain.restore_mempool(db)
            if restored:
                log.info("restored %d unsealed ballot(s) into the mempool", restored)
            election_ids = list(db.scalars(select(Election.id)))
            for problem in app.state.chain.startup_check(db, election_ids):
                log.warning("chain check: %s", problem)
                audit(db, None, "chain_mismatch_at_startup", reason=problem[:300])
                db.commit()
        task = asyncio.create_task(background_loop(app)) if settings.sealer_enabled else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    from pathlib import Path

    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    database.configure(settings.database_url)
    database.init_db()

    app = FastAPI(title=settings.app_title, lifespan=lifespan)
    app.state.settings = settings
    app.state.keys = ElectionKeyStore(settings.election_keys_dir)
    app.state.chain = ChainService(
        data_dir=settings.chain_data_dir,
        node_count=settings.node_count,
        difficulty=settings.pow_difficulty,
        block_size=settings.block_size,
        block_interval_seconds=settings.block_interval_seconds,
    )
    app.state.limiter = RateLimiter(settings.rate_limit_per_minute)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, error: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})

    for router in (auth_router, elections_router, receipts_router, admin_router, chain_router):
        app.include_router(router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
