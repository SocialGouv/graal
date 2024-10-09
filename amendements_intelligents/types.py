from enum import Enum
from typing import Any, Union

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


# List of patterns for each entity type
class EntityType(Enum):
    CODE = "code"
    LAW = "law"
    ORDONNANCE = "ordonnance"
