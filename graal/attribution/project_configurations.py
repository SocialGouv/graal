import logging
import logging.config
from typing import Callable

import pandas as pd

from graal.attribution.attribution_data_loader import AttributionDataLoader
from graal.attribution.attribution_handler import AttributionHandler
from graal.attribution.matchers.credit_table_matcher import CreditTableMatcher
from graal.attribution.matchers.keyword_matcher import KeywordMatcher
from graal.attribution.matchers.legal_document_matcher import LegalDocumentMatcher
from graal.custom_types import LegalDocumentType, ProjectName
from graal.utils.amendment_pre_processor import AmendmentPreProcessor

logging.config.fileConfig("logging.conf")


def get_attribution_handler_builder_func(project_name: ProjectName):
    project_to_builder: dict[ProjectName, Callable] = {
        "PLFSS": build_plfss_attribution_handler,
        "PLF": build_plf_attribution_handler,
    }

    return project_to_builder.get(project_name)


def build_plf_attribution_handler(
    config_excel: dict[str, pd.DataFrame],
) -> AttributionHandler:
    """Build attribution handler for PLF project."""
    name_to_user_info_mapping = AttributionDataLoader.load_name_to_user_info_mappings(
        config_excel
    )

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    keywords_df = AttributionDataLoader.load_keywords(
        excel_data=config_excel, acronym_mapping=acronym_mapping
    )

    # Load program and keyword mappings for credit table analysis
    program_to_attribution = AttributionDataLoader.load_programs(
        config_excel=config_excel
    )

    return AttributionHandler(
        matchers=[
            KeywordMatcher(
                keywords_df=keywords_df,
                allowed_columns={"Exposé amdt"},
            ),
            CreditTableMatcher(
                program_to_attribution=program_to_attribution,
                allowed_columns={"Corps amdt original"},
            ),
        ],
        default_attributions=AttributionDataLoader.load_default_attribution_mappings(
            config_excel
        ),
        name_to_user_info_mapping=name_to_user_info_mapping,
        columns_to_match_on=["Exposé amdt", "Corps amdt original"],
    )


def build_plfss_attribution_handler(
    config_excel: dict[str, pd.DataFrame],
) -> AttributionHandler:
    name_to_user_info_mapping = AttributionDataLoader.load_name_to_user_info_mappings(
        config_excel
    )

    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])
    keywords_df = AttributionDataLoader.load_keywords(
        excel_data=config_excel, acronym_mapping=acronym_mapping
    )

    codes_articles_df = AttributionDataLoader.load_codes_and_articles(config_excel)
    laws_articles_df = AttributionDataLoader.load_laws_and_articles(config_excel)
    ordonnances_articles_df = AttributionDataLoader.load_ordonnances_and_articles(
        config_excel
    )

    return AttributionHandler(
        matchers=[
            KeywordMatcher(
                keywords_df=keywords_df,
                allowed_columns={"Exposé amdt", "Corps amdt"},
            ),
            LegalDocumentMatcher(
                document_type=LegalDocumentType.CODE,
                documents_df=codes_articles_df,
                matcher_type="LEGAL_DOCUMENT_CODE",
                allowed_columns={"Corps amdt"},
            ),
            LegalDocumentMatcher(
                document_type=LegalDocumentType.LAW,
                documents_df=laws_articles_df,
                matcher_type="LEGAL_DOCUMENT_LAW",
                allowed_columns={"Corps amdt"},
            ),
            LegalDocumentMatcher(
                document_type=LegalDocumentType.ORDONNANCE,
                documents_df=ordonnances_articles_df,
                matcher_type="LEGAL_DOCUMENT_ORDONNANCE",
                allowed_columns={"Corps amdt"},
            ),
        ],
        default_attributions=AttributionDataLoader.load_default_attribution_mappings(
            config_excel
        ),
        name_to_user_info_mapping=name_to_user_info_mapping,
        columns_to_match_on=["Exposé amdt", "Corps amdt"],
    )
