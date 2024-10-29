from amendements_intelligents.attribution.attribution_matcher import AttributionMatcher


def test_fuzzy_match():
    amendment = {
        "amdt_idx": 1,
        "Corps amdt": "this is a sample amendment and now this extra doesn't match but the next one will text match with extra  spaces    too thanks montant m bla bla",
    }
    keywords = {"sample", "text", "example", "extra spaces too", "montant m"}

    result = AttributionMatcher.fuzzy_match(amendment, keywords)
    expected = [
        {"amdt_idx": 1, "keyword": "sample"},
        {"amdt_idx": 1, "keyword": "text"},
        {"amdt_idx": 1, "keyword": "extra spaces too"},
        {"amdt_idx": 1, "keyword": "montant m"},
    ]
    assert sorted(result, key=lambda x: x["keyword"]) == sorted(
        expected, key=lambda x: x["keyword"]
    )


def test_fuzzy_match_no_keywords():
    amendment = {
        "amdt_idx": 1,
        "Corps amdt": "this is a sample amendment text montant merveilleux",
    }
    keywords = {"example", "test", "montant m"}

    result = AttributionMatcher.fuzzy_match(amendment, keywords)
    assert not result
