"""
Seeds the in-memory database with user Ayaan and 9 games on startup.
Called from main.py at application startup.
"""
import uuid
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from database import get_db


GAMES = [
    {
        "game_name": "NEBULA DRIFTER",
        "genre": "space_shooter",
        "tags": ["2D Primary", "Bullet Hell"],
        "thumbnail": "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000&auto=format&fit=crop",
        "plays": 4823, "views": 18420, "likes": 342, "comments": 0, "shares": 89,
    },
    {
        "game_name": "VOID RUNNER",
        "genre": "endless_runner",
        "tags": ["Alt-Core", "High Speed"],
        "thumbnail": "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1000&auto=format&fit=crop",
        "plays": 12560, "views": 45200, "likes": 891, "comments": 0, "shares": 234,
    },
    {
        "game_name": "COSMIC SALVAGE",
        "genre": "space_shooter",
        "tags": ["Tactical", "Scavenger"],
        "thumbnail": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1000&auto=format&fit=crop",
        "plays": 2150, "views": 8900, "likes": 156, "comments": 0, "shares": 42,
    },
    {
        "game_name": "NEON HEIST",
        "genre": "platformer",
        "tags": ["Stealth", "Action"],
        "thumbnail": "https://images.unsplash.com/photo-1550684376-efcbd6e3f031?q=80&w=1000&auto=format&fit=crop",
        "plays": 8340, "views": 28700, "likes": 567, "comments": 0, "shares": 178,
    },
    {
        "game_name": "ASTRO MINER",
        "genre": "endless_runner",
        "tags": ["Resource", "Survival"],
        "thumbnail": "https://images.unsplash.com/photo-1454789548928-9efd52dc4031?q=80&w=1000&auto=format&fit=crop",
        "plays": 3450, "views": 12300, "likes": 234, "comments": 0, "shares": 67,
    },
    {
        "game_name": "QUANTUM LEAP",
        "genre": "puzzle",
        "tags": ["Logic", "Mind-bending"],
        "thumbnail": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1000&auto=format&fit=crop",
        "plays": 5670, "views": 21500, "likes": 412, "comments": 0, "shares": 134,
    },
    {
        "game_name": "PHANTOM GRID",
        "genre": "space_shooter",
        "tags": ["Retro", "Wave Defense"],
        "thumbnail": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=1000&auto=format&fit=crop",
        "plays": 7890, "views": 32100, "likes": 623, "comments": 0, "shares": 201,
    },
    {
        "game_name": "SYNTH ARENA",
        "genre": "platformer",
        "tags": ["Multiplayer", "Competitive"],
        "thumbnail": "https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?q=80&w=1000&auto=format&fit=crop",
        "plays": 15200, "views": 52400, "likes": 1045, "comments": 0, "shares": 312,
    },
    {
        "game_name": "DARK ORBIT",
        "genre": "space_shooter",
        "tags": ["Roguelite", "Perma-death"],
        "thumbnail": "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?q=80&w=1000&auto=format&fit=crop",
        "plays": 9100, "views": 38700, "likes": 789, "comments": 0, "shares": 256,
    },
]

SAMPLE_COMMENTS = [
    "This game is absolutely insane! The mechanics are so smooth.",
    "Love the art style, feels like a AAA game.",
    "Can we get a multiplayer mode? This would be epic with friends.",
    "The difficulty curve is perfect. Not too easy, not too hard.",
    "Been playing this for hours, can't stop.",
    "How did you make this with just a text prompt? Mind blown.",
    "The particle effects are gorgeous.",
    "This reminds me of classic arcade games but way more polished.",
    "Best game on Aether so far. Period.",
    "The sound design really pulls you in.",
    "Would love to see a sequel to this!",
    "Controls feel super responsive, great job.",
    "This is what AI game generation should look like.",
    "Shared this with all my friends, they love it too.",
    "The level design is surprisingly creative.",
    "Getting some serious retro vibes, love it.",
    "Can you make this available on mobile?",
    "The boss fight at the end is chef's kiss.",
    "Smooth 60fps even on my old laptop.",
    "This platform is the future of gaming.",
]

COMMENT_USERS = [
    "NeonWraith", "PixelPhantom", "StardustCoder", "ZeroGrav",
    "CyberPulse", "NovaDrift", "QuantumFox", "ByteRunner",
    "VoidWalker", "SynthWave42",
]

MOCK_BLUEPRINT: Dict[str, Any] = {
    "genre": "space_shooter",
    "playerConfig": {"speed": 200, "health": 3},
    "enemyConfig": {"count": 5, "speed": 100, "type": "chase"},
    "collectibleConfig": {"count": 10, "value": 10},
    "spatialLayout": {"enemySpawnZone": "top", "collectibleZone": "random"},
    "scoringParams": {"pointsPerKill": 50, "pointsPerCollect": 10},
    "winCondition": {"type": "score", "targetScore": 500},
    "lossCondition": {"type": "health_depleted"},
}


async def seed_database():
    """Seeds the in-memory DB with Ayaan's user and 9 games."""
    db = get_db()

    # Check if already seeded
    existing = await db["users"].find_one({"email": "ayaan@test.com"})
    if existing:
        print("[SEED] Database already seeded, skipping.")
        return

    print("[SEED] Seeding database with Ayaan's data...")

    # ─── Create user Ayaan ───
    user_id = str(uuid.uuid4())
    password_hash = hashlib.sha256("test123".encode()).hexdigest()

    user_doc = {
        "user_id": user_id,
        "email": "ayaan@test.com",
        "password_hash": password_hash,
        "display_name": "Ayaan",
        "subscription": "pro",
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
        "last_login": datetime.now(timezone.utc),
        "is_verified": True,
    }
    await db["users"].insert_one(user_doc)

    # ─── Create games ───
    game_ids = []
    for i, game_data in enumerate(GAMES):
        game_id = str(uuid.uuid4())
        game_ids.append(game_id)

        days_ago = random.randint(0, 21)
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23))

        blueprint = MOCK_BLUEPRINT.copy()
        blueprint["genre"] = game_data["genre"]

        game_doc = {
            "game_id": game_id,
            "user_id": user_id,
            "game_name": game_data["game_name"],
            "genre": game_data["genre"],
            "blueprint_json": blueprint,
            "is_public": True,
            "is_pinned": i < 2,
            "plays": game_data["plays"],
            "views": game_data["views"],
            "likes": game_data["likes"],
            "comments": 0,
            "shares": game_data["shares"],
            "thumbnail_url": game_data["thumbnail"],
            "tags": game_data["tags"],
            "created_at": created_at,
            "updated_at": created_at,
        }
        await db["saved_games"].insert_one(game_doc)

    # ─── Create comments ───
    for game_id in game_ids:
        num_comments = random.randint(3, 8)
        for _ in range(num_comments):
            commenter = random.choice(COMMENT_USERS)
            comment_text = random.choice(SAMPLE_COMMENTS)
            days_ago = random.randint(0, 14)

            comment_doc = {
                "comment_id": str(uuid.uuid4()),
                "game_id": game_id,
                "user_id": str(uuid.uuid4()),
                "display_name": commenter,
                "text": comment_text,
                "created_at": datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23)),
            }
            await db["game_comments"].insert_one(comment_doc)

        # Update comment count on game
        await db["saved_games"].update_one(
            {"game_id": game_id},
            {"$set": {"comments": num_comments}}
        )

    print(f"[SEED] Created user: Ayaan (ayaan@test.com / test123)")
    print(f"[SEED] Created {len(GAMES)} games with comments")
    print(f"[SEED] Ready to go!")
