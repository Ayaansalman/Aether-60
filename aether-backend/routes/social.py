from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from auth import get_current_user
from database import get_db
from datetime import datetime, timezone
import uuid

router = APIRouter()

# ─── Models ───

class CommentOut(BaseModel):
    comment_id: str
    game_id: str
    user_id: str
    display_name: str
    text: str
    created_at: datetime

class CommentIn(BaseModel):
    text: str

class LikeResponse(BaseModel):
    liked: bool
    total_likes: int

class ShareResponse(BaseModel):
    total_shares: int

# ─── Like ───

@router.post("/{game_id}/like", response_model=LikeResponse)
async def toggle_like(game_id: str, user=Depends(get_current_user)):
    """Toggle like on a game. If already liked, unlike it."""
    db = get_db()
    user_id = user["sub"]
    
    game = await db["saved_games"].find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    existing_like = await db["game_likes"].find_one({"game_id": game_id, "user_id": user_id})
    
    if existing_like:
        # Unlike
        await db["game_likes"].delete_one({"game_id": game_id, "user_id": user_id})
        await db["saved_games"].update_one(
            {"game_id": game_id},
            {"$inc": {"likes": -1}}
        )
        updated = await db["saved_games"].find_one({"game_id": game_id})
        total_likes = max(updated.get("likes", 0), 0) if updated else 0
        return LikeResponse(liked=False, total_likes=total_likes)
    else:
        # Like
        await db["game_likes"].insert_one({
            "like_id": str(uuid.uuid4()),
            "game_id": game_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        })
        await db["saved_games"].update_one(
            {"game_id": game_id},
            {"$inc": {"likes": 1}}
        )
        updated = await db["saved_games"].find_one({"game_id": game_id})
        total_likes = updated.get("likes", 0) if updated else 0
        return LikeResponse(liked=True, total_likes=total_likes)

# ─── Comments ───

@router.get("/{game_id}/comments", response_model=List[CommentOut])
async def get_comments(game_id: str):
    """Get all comments for a game."""
    db = get_db()
    
    game = await db["saved_games"].find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    cursor = db["game_comments"].find({"game_id": game_id}).sort("created_at", -1)
    comments = await cursor.to_list(length=200)
    return comments

@router.post("/{game_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(game_id: str, body: CommentIn, user=Depends(get_current_user)):
    """Add a comment to a game."""
    db = get_db()
    user_id = user["sub"]
    
    game = await db["saved_games"].find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    
    # Get display name
    user_doc = await db["users"].find_one({"user_id": user_id})
    display_name = user_doc.get("display_name", "Aether User") if user_doc else "Aether User"
    
    comment = {
        "comment_id": str(uuid.uuid4()),
        "game_id": game_id,
        "user_id": user_id,
        "display_name": display_name,
        "text": body.text.strip(),
        "created_at": datetime.now(timezone.utc),
    }
    await db["game_comments"].insert_one(comment)
    
    # Increment comment count on the game
    await db["saved_games"].update_one(
        {"game_id": game_id},
        {"$inc": {"comments": 1}}
    )
    
    return comment

@router.delete("/{game_id}/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comment(game_id: str, comment_id: str, user=Depends(get_current_user)):
    """Delete your own comment."""
    db = get_db()
    
    comment = await db["game_comments"].find_one({"comment_id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db["game_comments"].delete_one({"comment_id": comment_id})
    await db["saved_games"].update_one(
        {"game_id": game_id},
        {"$inc": {"comments": -1}}
    )
    return {"message": "Comment deleted"}

# ─── Share ───

@router.post("/{game_id}/share", response_model=ShareResponse)
async def share_game(game_id: str):
    """Increment share count (called when user copies share link)."""
    db = get_db()
    
    game = await db["saved_games"].find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    await db["saved_games"].update_one(
        {"game_id": game_id},
        {"$inc": {"shares": 1}}
    )
    updated = await db["saved_games"].find_one({"game_id": game_id})
    return ShareResponse(total_shares=updated.get("shares", 0) if updated else 0)

# ─── Check if user liked a game ───

@router.get("/{game_id}/liked")
async def check_liked(game_id: str, user=Depends(get_current_user)):
    """Check if the current user has liked a game."""
    db = get_db()
    existing = await db["game_likes"].find_one({"game_id": game_id, "user_id": user["sub"]})
    return {"liked": existing is not None}
