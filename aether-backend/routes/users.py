from fastapi import APIRouter, Depends, HTTPException
from models import UserProfileResponse, UserStats, GameResponse
from auth import get_current_user
from database import get_db
from datetime import datetime, timezone

router = APIRouter()

@router.get("/me", response_model=UserProfileResponse)
async def get_profile(user=Depends(get_current_user)):
    """Get the current user's profile with aggregated stats and deployed games."""
    db = get_db()
    user_id = user["sub"]
    
    # Get or create user doc
    user_doc = await db["users"].find_one({"user_id": user_id})
    if not user_doc:
        user_doc = {
            "user_id": user_id,
            "email": user.get("email", ""),
            "display_name": user.get("email", "").split("@")[0] if user.get("email") else "Aether User",
            "subscription": "pro",
            "created_at": datetime.now(timezone.utc),
        }
        await db["users"].insert_one(user_doc)
    
    # Aggregate stats from all user's games
    cursor = db["saved_games"].find({"user_id": user_id}).sort("created_at", -1)
    games = await cursor.to_list(length=100)
    
    total_plays = 0
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_shares = 0
    deployed_games = []
    
    for g in games:
        g.setdefault("is_pinned", False)
        g.setdefault("plays", 0)
        g.setdefault("views", 0)
        g.setdefault("likes", 0)
        g.setdefault("comments", 0)
        g.setdefault("shares", 0)
        
        total_plays += g.get("plays", 0)
        total_views += g.get("views", 0)
        total_likes += g.get("likes", 0)
        total_comments += g.get("comments", 0)
        total_shares += g.get("shares", 0)
        
        if g.get("is_public", False):
            deployed_games.append(g)
    
    stats = UserStats(
        total_games=len(games),
        total_plays=total_plays,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
    )
    
    return UserProfileResponse(
        user_id=user_id,
        email=str(user_doc["email"]) if user_doc.get("email") else None,
        display_name=str(user_doc.get("display_name", "Aether User")),
        subscription=str(user_doc.get("subscription", "free")),
        stats=stats,
        deployed_games=deployed_games,
    )

@router.patch("/me")
async def update_profile(updates: dict, user=Depends(get_current_user)):
    """Update user profile (display_name, subscription)."""
    db = get_db()
    user_id = user["sub"]
    
    allowed_fields = {"display_name", "subscription"}
    update_fields = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    await db["users"].update_one(
        {"user_id": user_id},
        {"$set": update_fields},
        upsert=True
    )
    return {"message": "Profile updated", "updated": update_fields}
