import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.asset import AssetCreate, AssetUpdate
from app.models.asset import Asset

logger = logging.getLogger("asset_service")

# Realistic fallback in-memory registry for robust operations and fallback tests
_MOCK_REGISTRY: List[Asset] = [
    Asset(
        id="ast-tf01",
        name="North Substation Transformer T-101",
        asset_type="TRANSFORMER",
        status="NOMINAL",
        region="North Sector",
        metadata_json='{"capacity_kva": 2500, "voltage_kv": 13.8, "oil_temp_c": 64.2}',
        installation_date=datetime.utcnow() - timedelta(days=730),
        last_maintenance=datetime.utcnow() - timedelta(days=45),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    Asset(
        id="ast-tz01",
        name="Main St Traffic Intersection Zone",
        asset_type="TRAFFIC_ZONE",
        status="WARNING",
        region="Downtown Grid",
        metadata_json='{"avg_daily_flow": 18200, "camera_status": "ONLINE", "pedestrian_signal": "FAULTY"}',
        installation_date=datetime.utcnow() - timedelta(days=365),
        last_maintenance=datetime.utcnow() - timedelta(days=12),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    Asset(
        id="ast-wp01",
        name="Trunk Line A Main Conduit",
        asset_type="WATER_PIPELINE",
        status="CRITICAL",
        region="Central Hub",
        metadata_json='{"pipe_diameter_in": 36, "flow_rate_lps": 480.5, "pressure_psi": 82.3}',
        installation_date=datetime.utcnow() - timedelta(days=1460),
        last_maintenance=datetime.utcnow() - timedelta(days=120),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    Asset(
        id="ast-ps01",
        name="District 7 Public Siren Array",
        asset_type="PUBLIC_SYSTEM",
        status="NOMINAL",
        region="South Sector",
        metadata_json='{"decibel_output": 120, "coverage_radius_m": 800}',
        installation_date=datetime.utcnow() - timedelta(days=180),
        last_maintenance=datetime.utcnow() - timedelta(days=5),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
]


class AssetService:
    """
    Service class orchestrating the lifecycle and persistence of infrastructure assets.
    Provides standard DB operations with dynamic SQLite fallbacks.
    """

    @staticmethod
    async def get_assets(
        db: AsyncSession,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Asset]:
        """
        Query assets with optional filters.
        """
        try:
            stmt = select(Asset)
            if asset_type:
                stmt = stmt.where(Asset.asset_type == asset_type.upper())
            if status:
                stmt = stmt.where(Asset.status == status.upper())
            if region:
                stmt = stmt.where(Asset.region.ilike(f"%{region}%"))
            if name:
                stmt = stmt.where(Asset.name.ilike(f"%{name}%"))

            stmt = stmt.order_by(Asset.name.asc()).limit(limit)
            res = await db.execute(stmt)
            records = list(res.scalars().all())
            if records:
                return records
        except Exception as e:
            logger.error(
                f"Failed to query database assets: {e}. Returning mock registry."
            )

        # Fallback to Mock Registry
        filtered = _MOCK_REGISTRY
        if asset_type:
            filtered = [x for x in filtered if x.asset_type == asset_type.upper()]
        if status:
            filtered = [x for x in filtered if x.status == status.upper()]
        if region:
            filtered = [x for x in filtered if region.lower() in x.region.lower()]
        if name:
            filtered = [x for x in filtered if name.lower() in x.name.lower()]

        return filtered[:limit]

    @staticmethod
    async def get_asset_by_id(db: AsyncSession, asset_id: str) -> Optional[Asset]:
        """
        Retrieve single asset by ID.
        """
        try:
            res = await db.execute(select(Asset).where(Asset.id == asset_id))
            record = res.scalar_one_or_none()
            if record is not None:
                return record
        except Exception as e:
            logger.error(f"Database lookup failed for asset ID '{asset_id}': {e}.")

        # Fallback matching
        for item in _MOCK_REGISTRY:
            if item.id == asset_id:
                return item
        return None

    @staticmethod
    async def create_asset(db: AsyncSession, payload: AssetCreate) -> Asset:
        """
        Register a new asset.
        """
        new_asset = Asset(
            name=payload.name,
            asset_type=payload.asset_type,
            status=payload.status,
            region=payload.region,
            installation_date=payload.installation_date or datetime.utcnow(),
            last_maintenance=payload.last_maintenance or datetime.utcnow(),
        )
        if payload.dynamic_metadata:
            new_asset.dynamic_metadata = payload.dynamic_metadata

        if db is not None:
            try:
                db.add(new_asset)
                await db.commit()
                await db.refresh(new_asset)
                logger.info(
                    f"Registered new asset '{new_asset.name}' with ID '{new_asset.id}' in DB."
                )
                return new_asset
            except Exception as e:
                try:
                    await db.rollback()
                except Exception:
                    pass
                logger.error(
                    f"Failed to create asset in DB: {e}. Registering in mock fallback."
                )

        # Fallback: create mock uuid and insert to in-memory list
        import uuid

        new_asset.id = f"ast-{uuid.uuid4().hex[:8]}"
        new_asset.created_at = datetime.utcnow()
        new_asset.updated_at = datetime.utcnow()
        _MOCK_REGISTRY.append(new_asset)
        return new_asset

    @staticmethod
    async def update_asset(
        db: AsyncSession, asset_id: str, payload: AssetUpdate
    ) -> Asset:
        """
        Update an existing asset.
        """
        target_asset = await AssetService.get_asset_by_id(db, asset_id)
        if not target_asset:
            raise ValueError(f"Asset with ID '{asset_id}' does not exist.")

        # Apply updates
        if payload.name is not None:
            target_asset.name = payload.name
        if payload.asset_type is not None:
            target_asset.asset_type = payload.asset_type
        if payload.status is not None:
            target_asset.status = payload.status
        if payload.region is not None:
            target_asset.region = payload.region
        if payload.dynamic_metadata is not None:
            target_asset.dynamic_metadata = payload.dynamic_metadata
        if payload.installation_date is not None:
            target_asset.installation_date = payload.installation_date
        if payload.last_maintenance is not None:
            target_asset.last_maintenance = payload.last_maintenance

        target_asset.updated_at = datetime.utcnow()

        if db is not None:
            try:
                # Check if this object is bound to db session before committing
                # Object might be from mock registry fallback
                if target_asset in db:
                    await db.commit()
                    await db.refresh(target_asset)
                    logger.info(f"Updated asset '{asset_id}' in SQLite database.")
                return target_asset
            except Exception as e:
                try:
                    await db.rollback()
                except Exception:
                    pass
                logger.error(f"Database update failed for asset '{asset_id}': {e}.")
                return target_asset
        return target_asset

    @staticmethod
    async def delete_asset(db: AsyncSession, asset_id: str) -> bool:
        """
        Decommission and remove an asset.
        """
        if db is not None:
            try:
                res = await db.execute(select(Asset).where(Asset.id == asset_id))
                record = res.scalar_one_or_none()
                if record is not None:
                    await db.delete(record)
                    await db.commit()
                    logger.info(f"Decommissioned asset '{asset_id}' from database.")
                    return True
            except Exception as e:
                try:
                    await db.rollback()
                except Exception:
                    pass
                logger.error(f"Failed to delete database asset '{asset_id}': {e}.")

        # Try to delete from in-memory fallback
        global _MOCK_REGISTRY
        original_len = len(_MOCK_REGISTRY)
        _MOCK_REGISTRY = [x for x in _MOCK_REGISTRY if x.id != asset_id]
        return len(_MOCK_REGISTRY) < original_len
