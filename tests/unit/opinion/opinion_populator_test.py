import pandas as pd

from graal.opinion.opinion_handler import OpinionHandler


def test_opinion_populator():
    amendments_data = {
        "Groupe": ["Group A", "Group B", "Group C"],
        "SomeOtherColumn": [1, 2, 3],
    }
    amendments_df = pd.DataFrame(amendments_data)
    group_to_default_opinion = {
        "Group A": "Favorable",
        "Group B": "Défavorable",
        "Group C": "Neutre",
    }

    populator = OpinionHandler(amendments_df, group_to_default_opinion)
    result_df = populator.populate()

    expected_opinions = ["Favorable", "Défavorable", "Neutre"]
    assert result_df["Avis du Gouvernement"].tolist() == expected_opinions
