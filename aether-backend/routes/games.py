from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List
from models import GameCreate, GameResponse, GameRename, GameUpdate, UserProfileResponse, UserStats
from auth import get_current_user
from database import get_db
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.get("/library", response_model=List[GameResponse])
async def get_library(user=Depends(get_current_user)):
    """Get all games for the authenticated user (sidebar history)."""
    db = get_db()
    cursor = db["saved_games"].find({"user_id": user["sub"]}).sort("created_at", -1)
    games = await cursor.to_list(length=100)
    for g in games:
        g.setdefault("is_pinned", False)
        g.setdefault("plays", 0)
        g.setdefault("views", 0)
        g.setdefault("likes", 0)
        g.setdefault("comments", 0)
        g.setdefault("shares", 0)
    return games

@router.get("/", response_model=List[GameResponse])
async def get_public_games():
    """Get all publicly shared games (Nexus feed)."""
    db = get_db()
    cursor = db["saved_games"].find({"is_public": True}).sort("created_at", -1)
    games = await cursor.to_list(length=100)
    for g in games:
        g.setdefault("is_pinned", False)
        g.setdefault("plays", 0)
        g.setdefault("views", 0)
        g.setdefault("likes", 0)
        g.setdefault("comments", 0)
        g.setdefault("shares", 0)
    return games

@router.post("/save", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def save_game(game: GameCreate, user=Depends(get_current_user)):
    """Save a new game to the user's library."""
    db = get_db()
    
    # Enforce 20-game limit
    count = await db["saved_games"].count_documents({"user_id": user["sub"]})
    if count >= 20:
        raise HTTPException(status_code=400, detail="Maximum limit of 20 saved games reached.")
        
    game_dict = game.model_dump()
    game_dict["game_id"] = str(uuid.uuid4())
    game_dict["user_id"] = user["sub"]
    game_dict["is_public"] = False
    game_dict["is_pinned"] = False
    game_dict["plays"] = 0
    game_dict["views"] = 0
    game_dict["likes"] = 0
    game_dict["comments"] = 0
    game_dict["shares"] = 0
    game_dict["created_at"] = datetime.now(timezone.utc)
    
    await db["saved_games"].insert_one(game_dict)
    return game_dict

@router.patch("/{game_id}", response_model=GameResponse)
async def update_game(game_id: str, update: GameUpdate, user=Depends(get_current_user)):
    """Update a game (rename, pin/unpin, publish). Used by sidebar context menu."""
    db = get_db()
    game = await db["saved_games"].find_one({"game_id": game_id})
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_fields: Dict[str, Any] = {}
    if update.game_name is not None:
        update_fields["game_name"] = update.game_name
    if update.is_pinned is not None:
        update_fields["is_pinned"] = update.is_pinned
    if update.is_public is not None:
        update_fields["is_public"] = update.is_public
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    await db["saved_games"].update_one(
        {"game_id": game_id},
        {"$set": update_fields}
    )
    
    updated = await db["saved_games"].find_one({"game_id": game_id})
    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")
    updated.setdefault("is_pinned", False)
    updated.setdefault("plays", 0)
    updated.setdefault("views", 0)
    updated.setdefault("likes", 0)
    updated.setdefault("comments", 0)
    updated.setdefault("shares", 0)
    return updated

@router.delete("/{game_id}", status_code=status.HTTP_200_OK)
async def delete_game(game_id: str, user=Depends(get_current_user)):
    """Delete a game from the user's library."""
    db = get_db()
    game = await db["saved_games"].find_one({"game_id": game_id})
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db["saved_games"].delete_one({"game_id": game_id})
    return {"message": "Game deleted successfully"}

@router.patch("/{game_id}/share")
async def share_game(game_id: str, user=Depends(get_current_user)):
    """Toggle a game's public visibility."""
    db = get_db()
    game = await db["saved_games"].find_one({"game_id": game_id})
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized to share this game")
        
    await db["saved_games"].update_one(
        {"game_id": game_id},
        {"$set": {"is_public": True, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Game shared successfully", "is_public": True}

@router.get("/{game_id}/stats")
async def get_game_stats(game_id: str):
    """Get stats for a single game."""
    db = get_db()
    game = await db["saved_games"].find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "plays": game.get("plays", 0),
        "views": game.get("views", 0),
        "likes": game.get("likes", 0),
        "comments": game.get("comments", 0),
        "shares": game.get("shares", 0),
    }
