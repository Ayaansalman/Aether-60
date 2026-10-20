from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

class User(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    subscription: str = "free"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    is_verified: bool = False

class GameCreate(BaseModel):
    game_name: str
    genre: str
    blueprint_json: Dict[str, Any]

class GameResponse(BaseModel):
    game_id: str
    user_id: str
    game_name: str
    genre: str
    blueprint_json: Dict[str, Any]
    is_public: bool
    is_pinned: bool = False
    plays: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    thumbnail_url: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

class GameRename(BaseModel):
    game_name: str

class GameUpdate(BaseModel):
    game_name: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_public: Optional[bool] = None

class UserStats(BaseModel):
    total_games: int = 0
    total_plays: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0

class UserProfileResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    subscription: str = "free"
    stats: UserStats = Field(default_factory=UserStats)
    deployed_games: List[GameResponse] = []

class CommentCreate(BaseModel):
    text: str

class GenerateRequest(BaseModel):
    prompt: str
    genre: Optional[str] = None
