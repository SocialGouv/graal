import os
import time

import pandas as pd

from amendements_intelligents.utils.content_similarity_evaluator import (
    ContentSimilarityEvaluator,
)
from amendements_intelligents.utils.plfss_text_processor import PLFSSTextProcessor

start_time = time.time()

DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
MIN_LENGTH_EXPOSE_TO_PROCESS = 50
previous_plfss_df = pd.read_json(f"{DATA_FOLDER}/PLFSS 2024.json")
previous_plfss_df["Year"] = 2024
print(f"Loaded {len(previous_plfss_df)} previous PLFSS amendments")

# TODO: replace these next few lines when processing real new amendments
# Simulate new amendments
amendments_to_process_df = previous_plfss_df.sample(n=int(0.2 * len(previous_plfss_df)))
amendments_to_process_df["Allotissement"] = None
amendments_to_process_df["Identique"] = None
amendments_to_process_df["Réponse"] = None
amendments_to_process_df["Sort"] = None
amendments_to_process_df["Commentaires"] = None
previous_plfss_df = previous_plfss_df[
    ~previous_plfss_df["Numéro"].isin(amendments_to_process_df["Numéro"])
]

print(f"Processing {len(amendments_to_process_df)} new amendments...")

old_amendments_df = PLFSSTextProcessor.preprocess_df(previous_plfss_df)
new_amendments_df = PLFSSTextProcessor.preprocess_df(amendments_to_process_df)

print("Prefiltering similar documents for optimization...")

similar_doc_indices = ContentSimilarityEvaluator.tf_idf_filtering(
    documents_to_search=old_amendments_df["Exposé des motifs"].tolist(),
    documents_to_filter=new_amendments_df["Exposé des motifs"].tolist(),
    threshold=0.4,
)
list_lengths = [len(docs) for docs in similar_doc_indices.values()]
average_length = sum(list_lengths) / len(list_lengths)
print(f"Average number of potential matches per amendment: {average_length}")

old_amendments = {
    "text": old_amendments_df["Exposé des motifs"],
    # We will keep the min comparison_value in `find_best_matching_docs`.
    # Since we want the most recent year, we will use the negative year to achieve that.
    "comparison_value": -old_amendments_df["Year"],
}
new_amendments = new_amendments_df["Exposé des motifs"]

closest_docs = ContentSimilarityEvaluator.find_best_matching_docs(
    similar_doc_indices=similar_doc_indices,
    left_docs=new_amendments,
    right_docs=old_amendments,
    threshold_ratio=0.95,
)
print(f"Found matches in previous PLFSS for {len(closest_docs)} amendments")

for new_idx, closest_doc in closest_docs.items():
    new_amendment_numero = new_amendments_df.iloc[new_idx]["Numéro"]
    lecture = new_amendments_df.iloc[new_idx]["Lecture"]
    mask = (amendments_to_process_df["Numéro"] == new_amendment_numero) & (
        amendments_to_process_df["Lecture"] == lecture
    )
    best_match_idx = closest_doc["best_matching_doc_idx"]

    amendments_to_process_df.loc[mask, "Réponse"] = old_amendments_df.iloc[
        best_match_idx
    ]["Réponse"]

    matching_numero = old_amendments_df.iloc[best_match_idx]["Numéro"]
    matching_pos = old_amendments_df.iloc[best_match_idx]["Lecture"]
    matching_year = -closest_doc["best_matching_comparison_value"]
    amendments_to_process_df.loc[mask, "Commentaires"] = f"""
    Réponse copiée du PLFSS {matching_year}
    Numéro d'amendement : {matching_numero}
    Lecture : {matching_pos}
    """

    old_sort_value = old_amendments_df.iloc[best_match_idx]["Sort"]

    if old_sort_value and "irrecevable" in old_sort_value.lower():
        amendments_to_process_df.loc[mask, "Sort"] = old_sort_value

amendments_to_process_df[
    [
        "Numéro",
        "Lecture",
        "Commentaires",
        "Réponse",
        "Exposé des motifs",
        "Sort",
        "Allotissement",
        "Identique",
    ]
].to_excel(f"{DATA_FOLDER}/amendments_with_similarity.xlsx", index=False)

print(f"Saved result in {DATA_FOLDER}/amendments_with_similarity.xlsx")

end_time = time.time()
execution_time = end_time - start_time
print(f"Script execution time: {execution_time} seconds")
