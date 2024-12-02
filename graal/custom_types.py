from enum import Enum
from typing import Any, Literal, TypedDict, Union

AmendementTxt = str
APIKey = str
CollectionMetadata = dict[str, Any]
ColumnName = str
CredentialsPassword = str
CredentialsUsername = str
ExpertiseDesc = str
ExpertiseID = str  # hash of ExpertDesc
IntIndex = int
LLMName = str
Metadata = Union[str, int, float]
Prompt = str
Seconds = int
Timestamp = int
TxtContent = str


ProjectName = Literal[
    "PLFSS",
    "PLACSS",
    "LFRSS",
    "PPL LIOT abrogation réforme des retraites",
    "PPL Retraites",
]


class ColumnsToWorkOn(TypedDict):
    to_preserve_orig_value: set[str]
    to_clear: set[str]


# List of patterns for each entity type
class EntityType(Enum):
    CODE = "code"
    LAW = "loi"
    ORDONNANCE = "ordonnance"


class InputFileConfig(TypedDict):
    default_processing_timestamp: Timestamp
    origin_project: ProjectName
    project_name_timestamp_delta: Seconds
