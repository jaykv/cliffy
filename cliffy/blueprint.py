from typing import Any, Type, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T", bound="Blueprint")


class Blueprint(BaseModel):
    """Base class for custom manifest blueprints that define CLI generation schemas"""

    name: str = Field(..., description="Name of the blueprint")
    version: str = Field(..., description="Version of the blueprint")
    help: str = Field(default="", description="Help text for the blueprint")
    loaded: datetime = Field(default_factory=datetime.now)

    def validate_hook(self) -> bool:
        """Hook for custom validation logic

        Returns:
            bool: True if validation passes, False otherwise
        """
        return True

    def load_hook(self) -> None:
        """Hook called when blueprint is loaded"""
        pass

    def init_hook(self) -> None:
        """Hook called during blueprint initialization"""
        pass

    def pre_process_hook(self) -> None:
        """Hook called before processing blueprint"""
        pass

    def post_process_hook(self) -> None:
        """Hook called after processing blueprint"""
        pass

    @classmethod
    def create(cls: Type[T], **data: Any) -> T:
        """Factory method to create a new blueprint instance

        Args:
            **data: Blueprint configuration data

        Returns:
            Blueprint instance
        """
        instance = cls(**data)
        instance.init_hook()
        return instance

    def process(self) -> None:
        """Main processing pipeline for the blueprint

        Executes hooks in order:
        1. pre_process_hook
        2. validate_hook
        3. load_hook
        4. post_process_hook
        """
        self.pre_process_hook()

        if not self.validate_hook():
            raise ValueError(f"Blueprint validation failed for {self.name}")

        self.load_hook()
        self.post_process_hook()
