from abc import ABC, abstractmethod

import chromadb

from amendements_intelligents.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingFunction,
)
from amendements_intelligents.types import (
    AmendementTxt,
    ExpertiseID,
    ExpertMetadata,
)


class ExpertiseVectorDB(ABC):
    @abstractmethod
    def add_expertise(self, expertise_dict: dict[ExpertiseID, ExpertMetadata]):
        raise NotImplementedError

    @abstractmethod
    def find_expert_for_amendements(
        self, amendements_texts: list[AmendementTxt], n_results: int = 1
    ):
        raise NotImplementedError


class ExpertiseChromaDB(ExpertiseVectorDB):
    def __init__(
        self,
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        vector_db_path="expertise_vector_db",
    ):
        self.client = chromadb.PersistentClient(path=vector_db_path)
        embedding_function = SentenceTransformerEmbeddingFunction(model_name=model_name)
        self.collection = self.client.get_or_create_collection(
            name="expertise_collection",
            embedding_function=embedding_function,
        )

    def add_expertise(self, expertise_dict: dict[ExpertiseID, ExpertMetadata]):
        metadatas = list(expertise_dict.values())
        deduplicated_descriptions = [
            metadata["expertise_desc"] for metadata in metadatas
        ]
        ids = list(expertise_dict.keys())
        if len(ids) > 0:
            self.collection.add(
                ids=ids, documents=deduplicated_descriptions, metadatas=metadatas
            )

    def find_expert_for_amendements(
        self, amendements_texts: list[AmendementTxt], n_results: int = 1
    ):
        # TODO: Add hybrid search + re-ranker
        results = self.collection.query(
            query_texts=amendements_texts, n_results=n_results
        )
        return results
