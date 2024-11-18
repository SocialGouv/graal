from enum import Enum
from typing import Any, TypedDict, Union

Vector = Union[list[float], list[int]]
Embedding = Vector

AmendementTxt = str
APIKey = str
CollectionMetadata = dict[str, Any]
ColumnName = str
CredentialsPassword = str
CredentialsUsername = str
Embeddings = list[Embedding]
ExpertiseDesc = str
ExpertiseID = str  # hash of ExpertDesc
IntIndex = int
Metadata = Union[str, int, float]
Prompt = str
TxtContent = str


class ColumnsToWorkOn(TypedDict):
    to_preserve_orig_value: set[str]
    to_clear: set[str]


# List of patterns for each entity type
class EntityType(Enum):
    CODE = "code"
    LAW = "loi"
    ORDONNANCE = "ordonnance"
