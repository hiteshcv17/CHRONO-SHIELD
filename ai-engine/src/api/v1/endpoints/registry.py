from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from src.ml.registry import ModelRegistryManager

router = APIRouter(prefix="/registry", tags=["Model Registry"])


class PromotionRequest(BaseModel):
    model_id: str = Field(..., description="The unique registered model ID to promote.")
    tier: str = Field(..., description="Target tier: PRODUCTION, STAGING, or CHALLENGER.")


class RollbackRequest(BaseModel):
    tier: str = Field(..., description="Target tier to perform rollback on.")


@router.get("/models", summary="List all registered models and active tiers")
def list_models(request: Request):
    """
    Retrieves the complete catalog of registered models, including hyperparameter metadata,
    validation metrics, active tier mappings, and promotion history.
    """
    try:
        registry = getattr(request.app.state, "registry", None)
        if not registry:
            registry = ModelRegistryManager()
        
        metadata = registry._load_metadata()
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch registry catalog: {str(e)}")


@router.post("/promote", summary="Promote model to active tier")
def promote_model(payload: PromotionRequest, request: Request):
    """
    Promotes a model to a specific active target tier. 
    Physically links the checkpoint to the target tier runner file.
    """
    try:
        registry = getattr(request.app.state, "registry", None)
        if not registry:
            registry = ModelRegistryManager()

        registry.promote_model(model_id=payload.model_id, tier=payload.tier)
        return {
            "status": "success",
            "message": f"Successfully promoted model '{payload.model_id}' to tier '{payload.tier.upper()}'."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Promotion failed: {str(e)}")


@router.post("/rollback", summary="Rollback tier to previous active model")
def rollback_tier(payload: RollbackRequest, request: Request):
    """
    Performs an atomic rollback of a target tier to its previously active model in history.
    """
    try:
        registry = getattr(request.app.state, "registry", None)
        if not registry:
            registry = ModelRegistryManager()

        registry.rollback_tier(tier=payload.tier)
        return {
            "status": "success",
            "message": f"Successfully rolled back tier '{payload.tier.upper()}' to previous active model checkpoint."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")
