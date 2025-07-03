from enum import Enum
from typing import Any, Dict, List, Literal, TypedDict, Union

Acronym = str
AmendementTxt = str
APIKey = str
CollectionMetadata = dict[str, Any]
ColumnName = str
CredentialsPassword = str
CredentialsUsername = str
ExpertiseDesc = str
ExpertiseID = str  # hash of ExpertDesc
IntIndex = int
Keyword = str
LLMName = str
Metadata = Union[str, int, float]
PLFProgramName = str
Prompt = str
RateLimitPerMinute = int
Seconds = int
Timestamp = int
TxtContent = str
UserName = str


class SimilarAmendment(TypedDict):
    """Information about a similar amendment."""

    amdt_num: int  # The amendment number (not index)
    similarity_percentage: float  # Similarity percentage (0-100)


# Maps amendment index to a list of similar amendments
SimilarityResult = Dict[int, List[SimilarAmendment]]

AttributionMatcherType = Literal[
    "LEGAL_DOCUMENT_CODE",
    "LEGAL_DOCUMENT_LAW",
    "LEGAL_DOCUMENT_ORDONNANCE",
    "KEYWORD",
    "CREDIT_TABLE",
    "REDACTIONAL_AMENDMENT",
]
LLMType = Literal[
    "ollama", "openai", "vllm", "llm_inference", "fake", "albert", "llama"
]
AttributionColumns = Literal["Exposé amdt", "Corps amdt", "Corps amdt original"]
ProjectName = Literal["PLFSS", "PLF"]


class ColumnsToWorkOn(TypedDict):
    to_preserve_orig_value: set[str]
    to_clear: set[str]


class LegalDocumentType(Enum):
    CODE = "code"
    LAW = "loi"
    ORDONNANCE = "ordonnance"


class InputFileConfig(TypedDict):
    default_processing_timestamp: Timestamp
    origin_project: str
