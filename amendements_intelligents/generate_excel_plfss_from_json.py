from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor


def main():
    plfss_preproc = PLFSSPreProcessor()
    FILE_NAME = "data/PLFSS_2022"
    plfss_preproc.load_plfss(f"{FILE_NAME}.json")
    df = plfss_preproc.clean_up_original_amendments()
    df.to_excel(f"{FILE_NAME}.xlsx", index=False)


if __name__ == "__main__":
    main()
