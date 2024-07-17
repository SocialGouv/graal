from amendements_intelligents.utils.text_utils import normalize_text


def test_normalize_text():
    assert (
        normalize_text("  Àpostrophe's-are `removed`  ") == "apostrophe s-are removed"
    )
    assert normalize_text("non-breaking space") == "non-breaking space"
    assert normalize_text("Éxámplè") == "example"
    assert normalize_text("!@#$%^&*()_+<>?") == ""
    assert (
        normalize_text(
            ": « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »"
        )
        == "les societes ont recu la certification du referentiel hebergeur de donnees de sante et des regles attachees a la norme iso 27001"
    )

    assert normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »"""
    ) == normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel hébergeur de données de santé et des règles attachées à la norme ISO 27001. »"""
    )
