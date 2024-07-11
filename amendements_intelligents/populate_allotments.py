import os
import time

import pandas as pd
from pydantic import FilePath
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from amendements_intelligents.types import IntIndex
from amendements_intelligents.utils.plfss_text_processor import PLFSSTextProcessor


class PLFSSDataProcessor:
    def __init__(self, input_file: FilePath):
        self.input_file = input_file
        self.columns_to_output = ["Numéro", "Allotissement", "Exposé des motifs"]
        self.amendments_df = None
        self.preprocessed_amendments_df = None

    def load_data(self) -> None:
        self.amendments_df = pd.read_json(self.input_file)
        self.amendments_df["Allotissement"] = None

    def preprocess_data(self) -> None:
        self.preprocessed_amendments_df = PLFSSTextProcessor.preprocess_df(
            self.amendments_df
        )
        print("PLFSS loaded for processing")


class PLFSSClusterFinder:
    def __init__(self, preprocessed_amendments_df: pd.DataFrame):
        self.preprocessed_amendments_df = preprocessed_amendments_df
        self.vectors = None
        self.distance_matrix = None
        self.final_clusters = None

    def vectorize_data(self) -> None:
        print("Converting strings to TF-IDF vectors...")
        strings = self.preprocessed_amendments_df["Exposé des motifs"].tolist()
        vectorizer = TfidfVectorizer()
        self.vectors = vectorizer.fit_transform(strings)

    def compute_distance_matrix(self) -> None:
        print("Computing cosine similarity matrix...")
        similarity_matrix = cosine_similarity(self.vectors)
        distance_matrix = 1 - similarity_matrix
        distance_matrix[distance_matrix < 0] = 0  # Ensure no negative values
        self.distance_matrix = distance_matrix

    def find_clusters(self) -> None:
        print("Finding clusters...")
        dbscan = DBSCAN(metric="precomputed", eps=0.5, min_samples=2)
        clusters = dbscan.fit_predict(self.distance_matrix)

        # Extract clusters
        clustered_strings = {}
        for idx, label in enumerate(clusters):
            if label == -1:  # Ignore noise points
                continue
            if label not in clustered_strings:
                clustered_strings[label] = []
            clustered_strings[label].append(idx)

        # Filter out singleton clusters
        self.final_clusters = [
            cluster for cluster in clustered_strings.values() if len(cluster) > 1
        ]
        print("Number of clusters:", len(self.final_clusters))


class AllotmentUpdater:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        preprocessed_amendments_df: pd.DataFrame,
        final_clusters: list[list[IntIndex]],
    ) -> None:
        self.amendments_df = amendments_df
        self.preprocessed_amendments_df = preprocessed_amendments_df
        self.final_clusters = final_clusters

    def update_allotissement(self) -> None:
        for cluster_indices in self.final_clusters:
            cluster_numeros = sorted(
                self.preprocessed_amendments_df.iloc[idx]["Numéro"]
                for idx in cluster_indices
            )
            cluster_numeros_str = ",".join(map(str, cluster_numeros))
            for idx in cluster_indices:
                amendment_numero = self.preprocessed_amendments_df.iloc[idx]["Numéro"]
                lecture = self.preprocessed_amendments_df.iloc[idx]["Lecture"]
                mask = (self.amendments_df["Numéro"] == amendment_numero) & (
                    self.amendments_df["Lecture"] == lecture
                )
                self.amendments_df.loc[mask, "Allotissement"] = cluster_numeros_str


def main():
    start_time = time.time()
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    INPUT_FILE = f"{DATA_FOLDER}/PLFSS 2024.json"
    OUTPUT_FILE = f"{DATA_FOLDER}/amendments_with_allotissement.xlsx"

    # Data processing
    plfss_data_processor = PLFSSDataProcessor(input_file=INPUT_FILE)
    plfss_data_processor.load_data()
    plfss_data_processor.preprocess_data()

    # Clustering
    cluster_finder = PLFSSClusterFinder(
        preprocessed_amendments_df=plfss_data_processor.preprocessed_amendments_df
    )
    cluster_finder.vectorize_data()
    cluster_finder.compute_distance_matrix()
    cluster_finder.find_clusters()

    # Result processing
    allotment_updater = AllotmentUpdater(
        amendments_df=plfss_data_processor.amendments_df,
        preprocessed_amendments_df=plfss_data_processor.preprocessed_amendments_df,
        final_clusters=cluster_finder.final_clusters,
    )

    allotment_updater.update_allotissement()
    allotment_updater.amendments_df[plfss_data_processor.columns_to_output].to_excel(
        OUTPUT_FILE, index=False
    )
    print(f"Saved result in {OUTPUT_FILE}")

    # Print execution time
    end_time = time.time()
    execution_time = end_time - start_time
    print("Script execution time:", execution_time, "seconds")


if __name__ == "__main__":
    main()
