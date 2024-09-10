import textwrap

import pandas as pd


class SimilarAmendmentCopier:
    # TODO: Get rid of this class, we could simply make `copy_matches_to_plfss_df` into a staticmethod in SimilarityHandler
    def __init__(
        self,
        new_amendments_df: pd.DataFrame,
        old_amendments_df: pd.DataFrame,
        closest_amdts: dict,
    ):
        self.new_amendments_df = new_amendments_df
        self.old_amendments_df = old_amendments_df
        self.closest_amdts = closest_amdts

    def copy_matches_to_plfss_df(self, target_df: pd.DataFrame) -> pd.DataFrame:
        # Iterate over the closest documents
        for new_amdt_idx, closest_doc in self.closest_amdts.items():
            # Retrieve the amendment number and lecture from the new amendments
            new_amendment_mask = self.new_amendments_df["amdt_idx"] == new_amdt_idx
            new_amendment_numero = self.new_amendments_df.loc[
                new_amendment_mask, "Num amdt"
            ].values[0]

            new_amendment_lecture = self.new_amendments_df.loc[new_amendment_mask][
                "Lecture"
            ].values[0]

            # Create a mask for the target DataFrame to find the matching rows
            new_amendment_mask = (target_df["Num amdt"] == new_amendment_numero) & (
                target_df["Lecture"] == new_amendment_lecture
            )

            # Get the best match details
            best_matching_doc_amdt_idx = closest_doc["best_matching_doc_amdt_idx"]
            column_used_for_comparison = closest_doc["column_used_for_comparison"]

            # Filter old amendments for the best match
            old_amendment_mask = (
                self.old_amendments_df["amdt_idx"] == best_matching_doc_amdt_idx
            )
            matching_amendment = self.old_amendments_df.loc[old_amendment_mask]

            if not matching_amendment.empty:
                # Copy the response if available
                target_df.loc[new_amendment_mask, "Réponse"] = matching_amendment[
                    "Réponse"
                ].values[0]

                # Extract the matching details
                matching_num_amdt = matching_amendment["Num amdt"].values[0]
                matching_lecture = matching_amendment["Lecture"].values[0]
                matching_organe = matching_amendment["Organe"].values[0]
                matching_year = -closest_doc["best_matching_comparison_value"]

                # Update target DataFrame with the matched details
                target_df.loc[new_amendment_mask, "Commentaires"] = textwrap.dedent(f"""
                Réponse copiée du PLFSS {matching_year}
                Numéro d'amendement : {matching_num_amdt}
                Lecture : {matching_lecture}
                Organe : {matching_organe}
                Colonne similaire : {column_used_for_comparison}
                """).strip()

                # Check and copy the "Sort" value if it contains "Irrecevable"
                old_sort_value = matching_amendment["Sort"].values[0]
                if pd.notna(old_sort_value) and "irrecevable" in old_sort_value.lower():
                    target_df.loc[new_amendment_mask, "Sort"] = old_sort_value

        return target_df
