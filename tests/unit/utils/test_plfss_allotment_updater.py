import pandas as pd
import pytest

from amendements_intelligents.utils.plfss_allotment_updater import (
    PLFSSAllotmentUpdater,
)


@pytest.fixture
def amendments_df():
    amendments_data = {
        "Num amdt": [1, 2, 3, 4, 5, 6],
        "Lecture": ["First", "First", "Second", "Second", "First", "First"],
        "Allotissement": [None, None, None, None, None, None],
    }
    amendments_df = pd.DataFrame(amendments_data)
    return amendments_df


@pytest.fixture
def preprocessed_amendments_df():
    preprocessed_amendments_data = {
        "Num amdt": [1, 2, 3, 4, 5, 6],
        "Lecture": ["First", "First", "Second", "Second", "First", "First"],
    }
    preprocessed_amendments_df = pd.DataFrame(preprocessed_amendments_data)
    return preprocessed_amendments_df


@pytest.fixture
def final_clusters():
    return {
        "First": [[0, 2], [1, 3]],
        "Second": [[0, 1]],
    }


def test_update_allotissement(
    amendments_df, preprocessed_amendments_df, final_clusters
):
    expected_amendments_data = {
        "Num amdt": [1, 2, 3, 4, 5, 6],
        "Lecture": ["First", "First", "Second", "Second", "First", "First"],
        "Allotissement": ["1,5", "2,6", "3,4", "3,4", "1,5", "2,6"],
    }
    expected_amendments_df = pd.DataFrame(expected_amendments_data)

    updater = PLFSSAllotmentUpdater(
        amendments_df, preprocessed_amendments_df, final_clusters
    )
    result_df = updater.update_allotissement()

    pd.testing.assert_frame_equal(result_df, expected_amendments_df)


def test_empty_clusters(amendments_df, preprocessed_amendments_df):
    final_clusters = {}

    updater = PLFSSAllotmentUpdater(
        amendments_df, preprocessed_amendments_df, final_clusters
    )
    result_df = updater.update_allotissement()

    pd.testing.assert_frame_equal(result_df, amendments_df)


def test_single_entry_cluster(amendments_df, preprocessed_amendments_df):
    final_clusters = {
        "First": [[0]],
    }

    expected_amendments_data = {
        "Num amdt": [1, 2, 3, 4, 5, 6],
        "Lecture": ["First", "First", "Second", "Second", "First", "First"],
        "Allotissement": ["1", None, None, None, None, None],
    }
    expected_amendments_df = pd.DataFrame(expected_amendments_data)

    updater = PLFSSAllotmentUpdater(
        amendments_df, preprocessed_amendments_df, final_clusters
    )
    result_df = updater.update_allotissement()

    pd.testing.assert_frame_equal(result_df, expected_amendments_df)


def test_multiple_clusters_same_lecture(amendments_df, preprocessed_amendments_df):
    final_clusters = {
        "First": [[0, 2], [1]],
    }

    expected_amendments_data = {
        "Num amdt": [1, 2, 3, 4, 5, 6],
        "Lecture": ["First", "First", "Second", "Second", "First", "First"],
        "Allotissement": ["1,5", "2", None, None, "1,5", None],
    }
    expected_amendments_df = pd.DataFrame(expected_amendments_data)

    updater = PLFSSAllotmentUpdater(
        amendments_df, preprocessed_amendments_df, final_clusters
    )
    result_df = updater.update_allotissement()

    pd.testing.assert_frame_equal(result_df, expected_amendments_df)
