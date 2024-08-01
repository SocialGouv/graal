import textwrap

import pandas as pd


class AmendmentCopier:
    def __init__(
        self,
        new_amendments_df: pd.DataFrame,
        old_amendments_df: pd.DataFrame,
        closest_docs: dict,
    ):
        self.new_amendments_df = new_amendments_df
        self.old_amendments_df = old_amendments_df
        self.closest_docs = closest_docs

    def copy_matches_to_plfss_df(self, target_df: pd.DataFrame):
        for new_idx, closest_doc in self.closest_docs.items():
            new_amendment_numero = self.new_amendments_df.iloc[new_idx]["Num amdt"]
            new_amendment_lecture = self.new_amendments_df.iloc[new_idx]["Lecture"]
            mask = (target_df["Num amdt"] == new_amendment_numero) & (
                target_df["Lecture"] == new_amendment_lecture
            )
            best_match_idx = closest_doc["best_matching_doc_idx"]

            target_df.loc[mask, "Réponse"] = self.old_amendments_df.iloc[
                best_match_idx
            ]["Réponse"]

            matching_numero = self.old_amendments_df.iloc[best_match_idx]["Num amdt"]
            matching_lecture = self.old_amendments_df.iloc[best_match_idx]["Lecture"]
            matching_corps = self.old_amendments_df.iloc[best_match_idx]["Corps amdt orig"]
            matching_expose = self.old_amendments_df.iloc[best_match_idx]["Exposé amdt orig"]
            matching_year = -closest_doc["best_matching_comparison_value"]

            target_df.loc[mask, "Commentaires"] = textwrap.dedent(f"""
            Réponse copiée du PLFSS {matching_year}
            Lecture : {matching_lecture}
            Numéro d'amendement : {matching_numero}
            """)

            target_df.loc[mask, "Corps amdt trouvé"] = matching_corps
            target_df.loc[mask, "Exposé amdt trouvé"] = matching_expose

            old_sort_value = self.old_amendments_df.iloc[best_match_idx]["Sort"]
            if old_sort_value and "irrecevable" in old_sort_value.lower():
                target_df.loc[mask, "Sort"] = old_sort_value
        return target_df
