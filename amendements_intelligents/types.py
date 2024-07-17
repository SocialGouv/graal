from typing import Any, TypedDict, Union

Vector = Union[list[float], list[int]]
Embedding = Vector

AmendementTxt = str
APIKey = str
CollectionMetadata = dict[str, Any]
ColumnName = str
Embeddings = list[Embedding]
ExpertiseDesc = str
ExpertiseID = str  # hash of ExpertDesc
IntIndex = int
Metadata = Union[str, int, float]
Prompt = str
TxtContent = str


class ExpertMetadata(TypedDict):
    expertise_desc: ExpertiseDesc
    # I would like `experts_as_str` to be a list but the VectorDB we are using does not support it
    experts_as_str: str
