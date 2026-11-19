from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class PostType(str, Enum):
    job = "job"
    internship = "internship"
    trainee = "trainee"
    fellowship = "fellowship"
    course_or_workshop = "course_or_workshop"
    event = "event"
    other = "other"


class Role(str, Enum):
    software_dev = "software_dev"
    data_analytics = "data_analytics"
    ml_ai = "ml_ai"
    it_devops_security = "it_devops_security"
    qa_testing = "qa_testing"
    product_management = "product_management"
    design = "design"
    marketing = "marketing"
    sales_bd = "sales_bd"
    customer_support = "customer_support"
    admin_back_office = "admin_back_office"
    human_resources = "human_resources"
    hr_recruitment = "hr_recruitment"
    finance_accounting = "finance_accounting"
    finance_banking = "finance_banking"
    operations_supply_chain = "operations_supply_chain"
    operations_logistics = "operations_logistics"
    content_writing = "content_writing"
    research = "research"
    teaching_education = "teaching_education"
    core_engineering = "core_engineering"
    healthcare = "healthcare"
    legal_compliance = "legal_compliance"
    hospitality_retail = "hospitality_retail"
    other = "other"


class City(str, Enum):
    bengaluru = "bengaluru"
    hyderabad = "hyderabad"
    pune = "pune"
    mumbai = "mumbai"
    delhi_ncr = "delhi_ncr"
    chennai = "chennai"
    kolkata = "kolkata"
    ahmedabad = "ahmedabad"
    other_india = "other_india"
    remote = "remote"
    unknown = "unknown"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    status: str = "success"


class TagResult(BaseModel):
    index: int
    post_type: PostType
    is_fresher: bool
    role: Role
    city: City
    is_remote: bool = False

    @model_validator(mode="after")
    def compute_is_remote(self) -> "TagResult":
        # Remote flag is directly derived from city enum to save token output
        if self.city == City.remote:
            self.is_remote = True
        return self


class BaseLLMProvider(ABC):
    """Abstract interface for LLM job taggers."""

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def tag_batch(
        self,
        posts: list[dict[str, Any]],
        prompt_version: str = "tag_v1",
    ) -> tuple[list[TagResult], Usage]:
        """Tag a batch of job posts and return validated results plus usage metrics."""
        pass
