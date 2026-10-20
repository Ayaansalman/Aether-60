from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routes import games, generate, users, auth, social, games_v1, platformer
from seed_data import seed_database
from services.job_store import mark_interrupted_jobs_on_startup
from services.event_store import add_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed database
    await seed_database()
    # Mark any unfinished jobs from prior process as FAILED (interrupted by restart)
    interrupted_ids = mark_interrupted_jobs_on_startup()
    for gid in interrupted_ids:
        add_event(
            gid,
            stage="INTERNAL_ERROR",
            result="FAILED",
            detail="interrupted by restart",
            attempt=1,
        )
    yield
    # Shutdown: nothing to clean up for in-memory


app = FastAPI(title="AETHER Backend API", version="1.0.0", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(games.router, prefix="/api/games", tags=["Games"])
app.include_router(social.router, prefix="/api/games", tags=["Social"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(games_v1.router, prefix="/api/v1", tags=["Games v1"])
app.include_router(platformer.router, prefix="/api/v2", tags=["Generation v2"])

@app.get("/")
async def root():
    return {"message": "AETHER Backend API is running"}
