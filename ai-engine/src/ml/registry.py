import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("model_registry")


class ModelRegistryManager:
    """
    Model Registry managing checkpoints, metadata indexing, and promotion tiers.
    Supported tiers: PRODUCTION, STAGING, CHALLENGER.
    """

    def __init__(self, registry_dir: str = "./ai-engine/models/registry"):
        self.registry_dir = registry_dir
        self.metadata_path = os.path.join(self.registry_dir, "registry_metadata.json")
        os.makedirs(self.registry_dir, exist_ok=True)
        self._init_metadata()

    def _init_metadata(self) -> None:
        if not os.path.exists(self.metadata_path):
            self._save_metadata(
                {
                    "models": {},
                    "tiers": {"PRODUCTION": None, "STAGING": None, "CHALLENGER": None},
                }
            )

    def _load_metadata(self) -> Dict[str, Any]:
        try:
            with open(self.metadata_path, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "models": {},
                "tiers": {"PRODUCTION": None, "STAGING": None, "CHALLENGER": None},
            }

    def _save_metadata(self, data: Dict[str, Any]) -> None:
        with open(self.metadata_path, "w") as f:
            json.dump(data, f, indent=4)

    def register_model(
        self,
        model_id: str,
        checkpoint_path: str,
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        model_type: str = "pytorch",
    ) -> Dict[str, Any]:
        """
        Registers a new model checkpoint under the registry directory.
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")

        # Copy checkpoint into the registry directory
        filename = f"{model_id}_{os.path.basename(checkpoint_path)}"
        dest_path = os.path.join(self.registry_dir, filename)
        shutil.copy2(checkpoint_path, dest_path)

        metadata = self._load_metadata()
        entry = {
            "model_id": model_id,
            "registered_at": datetime.utcnow().isoformat(),
            "checkpoint_file": filename,
            "checkpoint_path": os.path.abspath(dest_path),
            "parameters": parameters,
            "metrics": metrics,
            "model_type": model_type,
            "history": [],
        }
        metadata["models"][model_id] = entry
        self._save_metadata(metadata)
        logger.info(f"Successfully registered model '{model_id}' under: {dest_path}")
        return entry

    def promote_model(self, model_id: str, tier: str) -> None:
        """
        Promotes a model to a target tier (PRODUCTION, STAGING, CHALLENGER).
        """
        tier = tier.upper()
        if tier not in ["PRODUCTION", "STAGING", "CHALLENGER"]:
            raise ValueError(f"Invalid promotion tier: {tier}")

        metadata = self._load_metadata()
        if model_id not in metadata["models"]:
            raise ValueError(
                f"Model ID '{model_id}' is not registered in the registry."
            )

        old_active = metadata["tiers"].get(tier)
        metadata["tiers"][tier] = model_id

        # Record promotion history
        history_entry = {
            "action": f"PROMOTED_TO_{tier}",
            "timestamp": datetime.utcnow().isoformat(),
            "previous_active": old_active,
        }
        metadata["models"][model_id]["history"].append(history_entry)

        # physically copy/link the target checkpoint file to standard tier name
        source_checkpoint = metadata["models"][model_id]["checkpoint_path"]
        tier_filename = f"autoencoder_{tier.lower()}.pth"
        tier_dest = os.path.join(self.registry_dir, tier_filename)
        shutil.copy2(source_checkpoint, tier_dest)

        self._save_metadata(metadata)
        logger.info(
            f"Model '{model_id}' promoted to tier: {tier}. Checkpoint active: {tier_dest}"
        )

    def get_tier_checkpoint(self, tier: str) -> Optional[str]:
        """
        Retrieves the exact absolute checkpoint path for a promoted tier.
        """
        tier = tier.upper()
        tier_filename = f"autoencoder_{tier.lower()}.pth"
        path = os.path.join(self.registry_dir, tier_filename)
        if os.path.exists(path):
            return os.path.abspath(path)
        return None

    def rollback_tier(self, tier: str) -> None:
        """
        Rolls back the target tier to the previous active model checkpoint.
        """
        tier = tier.upper()
        metadata = self._load_metadata()
        current_active = metadata["tiers"].get(tier)
        if not current_active:
            raise ValueError(
                f"No active model currently promoted to tier '{tier}' to perform a rollback."
            )

        history = metadata["models"][current_active]["history"]
        previous_active = None
        for entry in reversed(history):
            if entry["action"] == f"PROMOTED_TO_{tier}":
                previous_active = entry.get("previous_active")
                break

        if not previous_active:
            raise ValueError(
                f"No previous active model found in history for tier '{tier}' to rollback to."
            )

        # Re-promote the previous model
        self.promote_model(previous_active, tier)
        logger.info(
            f"Tier '{tier}' rolled back from model '{current_active}' to previous model '{previous_active}'."
        )
