from fastapi import APIRouter, Depends, HTTPException, status
from models import GenerateRequest
from auth import get_current_user
import asyncio
import json

router = APIRouter()

MOCK_BLUEPRINT = {
    "genre": "space_shooter",
    "playerConfig": { "speed": 200, "health": 3 },
    "enemyConfig": { "count": 5, "speed": 100, "type": "chase" },
    "collectibleConfig": { "count": 10, "value": 10 },
    "spatialLayout": {
        "enemySpawnZone": "top",
        "collectibleZone": "random"
    },
    "scoringParams": { "pointsPerKill": 50, "pointsPerCollect": 10 },
    "winCondition": {
        "type": "score",
        "targetScore": 500
    },
    "lossCondition": { "type": "health_depleted" }
}

@router.post("/", status_code=status.HTTP_200_OK)
async def generate_game(request: GenerateRequest, user=Depends(get_current_user)):
    # Simulate processing time for parsing, generating, validating, and assembling
    await asyncio.sleep(2.0)
    
    # In a real implementation, this would call the AI pipeline.
    # We return the mocked blueprint.
    blueprint = MOCK_BLUEPRINT.copy()
    if request.genre:
        blueprint["genre"] = request.genre.lower()
        
    return {
        "message": "Game generated successfully",
        "blueprint": blueprint
    }
