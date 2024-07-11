from typing import Any, TypedDict, Union

TxtContent = str
AmendementTxt = str
Prompt = str
APIKey = str
Vector = Union[list[float], list[int]]
Embedding = Vector
Embeddings = list[Embedding]
CollectionMetadata = dict[str, Any]
ExpertiseDesc = str
Metadata = Union[str, int, float]
ExpertiseID = str  # hash of ExpertDesc
IntIndex = int


class ExpertMetadata(TypedDict):
    expertise_desc: ExpertiseDesc
    # I would like `experts_as_str` to be a list but the VectorDB we are using does not support it
    experts_as_str: str
