from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.asset import AssetResponse, AssetCreate, AssetUpdate
from app.services.asset_service import AssetService
from app.core.auth import require_viewer, require_analyst, require_admin
from app.utils.cache import cache_response, invalidate_cache_by_pattern
from app.utils.constants import CacheTTL

router = APIRouter()


@router.get("", response_model=List[AssetResponse], status_code=status.HTTP_200_OK)
@cache_response(ttl=CacheTTL.ASSETS.value, prefix="assets")
async def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by operational status"),
    region: Optional[str] = Query(None, description="Filter by operational region"),
    name: Optional[str] = Query(None, description="Filter by asset name (fuzzy search)"),
    limit: int = Query(50, ge=1, le=100, description="Retrieve limit"),
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(require_viewer)
) -> List[AssetResponse]:
    """
    Retrieve logs of registered physical infrastructure assets.
    """
    assets = await AssetService.get_assets(
        db,
        asset_type=asset_type,
        status=status_filter,
        region=region,
        name=name,
        limit=limit
    )
    return [AssetResponse.model_validate(a) for a in assets]


@router.get("/{asset_id}", response_model=AssetResponse, status_code=status.HTTP_200_OK)
@cache_response(ttl=CacheTTL.ASSETS.value, prefix="assets")
async def get_asset_by_id(
    asset_id: str,
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(require_viewer)
) -> AssetResponse:
    """
    Retrieve a single infrastructure asset's detailed schema and dynamic metadata.
    """
    asset = await AssetService.get_asset_by_id(db, asset_id=asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found."
        )
    return AssetResponse.model_validate(asset)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def register_new_asset(
    payload: AssetCreate,
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(require_analyst)
) -> AssetResponse:
    """
    Register a new physical infrastructure asset under database monitoring.
    """
    res = await AssetService.create_asset(db, payload=payload)
    await invalidate_cache_by_pattern("assets:*")
    return res


@router.put("/{asset_id}", response_model=AssetResponse, status_code=status.HTTP_200_OK)
async def modify_registered_asset(
    asset_id: str,
    payload: AssetUpdate,
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(require_analyst)
) -> AssetResponse:
    """
    Modify attributes or dynamic key-value metadata logs of an active asset.
    """
    try:
        res = await AssetService.update_asset(db, asset_id=asset_id, payload=payload)
        await invalidate_cache_by_pattern("assets:*")
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def decommission_registered_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin)
):
    """
    Decommission and remove an asset record from database tracking registries.
    """
    deleted = await AssetService.delete_asset(db, asset_id=asset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found or could not be deleted."
        )
    await invalidate_cache_by_pattern("assets:*")
    return status.HTTP_204_NO_CONTENT
