from abc import ABC, abstractmethod
from typing import Any

class BaseModel(ABC):
    """
    Abstract Base Class for all anomaly detection models in ChronoShield AI.
    Guarantees consistent interfaces for training, inference, and serialization.
    """

    @abstractmethod
    def fit(self, X: Any, **kwargs: Any) -> Any:
        """
        Train the model on the provided data.
        """
        pass

    @abstractmethod
    def predict(self, X: Any, **kwargs: Any) -> Any:
        """
        Perform inference and predict anomaly scores or flags.
        """
        pass

    @abstractmethod
    def save(self, path: str, **kwargs: Any) -> str:
        """
        Serialize model state and save to the specified file path.
        """
        pass

    @abstractmethod
    def load(self, path: str, **kwargs: Any) -> None:
        """
        Restore model state from the specified checkpoint path.
        """
        pass
