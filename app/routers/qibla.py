"""Qibla direction + mosque finder"""
from fastapi import APIRouter, HTTPException, Query
from app.core.dependencies import CurrentUser
from app.services.qibla_service import calculate_qibla, find_nearby_mosques

router = APIRouter(prefix="/qibla", tags=["qibla"])


@router.get("")
async def get_qibla(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    return calculate_qibla(lat, lng)


@router.get("/me")
async def get_qibla_for_user(current_user: CurrentUser):
    if not current_user.latitude or not current_user.longitude:
        raise HTTPException(status_code=422, detail="Location not set. Update your profile.")
    return calculate_qibla(current_user.latitude, current_user.longitude)


@router.get("/mosques")
async def nearby_mosques(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: int = Query(default=5000, le=20000),
    limit: int = Query(default=20, le=50),
):
    try:
        mosques = await find_nearby_mosques(lat, lng, radius_m=radius_m, limit=limit)
        return {"count": len(mosques), "mosques": mosques}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Mosque finder temporarily unavailable: {e}")


@router.get("/mosques/nearby")
async def mosques_near_me(
    current_user: CurrentUser,
    radius_m: int = Query(default=5000, le=20000),
):
    if not current_user.latitude or not current_user.longitude:
        raise HTTPException(status_code=422, detail="Location not set.")
    try:
        mosques = await find_nearby_mosques(current_user.latitude, current_user.longitude, radius_m=radius_m)
        return {"count": len(mosques), "mosques": mosques}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Mosque finder temporarily unavailable: {e}")
