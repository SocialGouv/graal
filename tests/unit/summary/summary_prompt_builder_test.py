from graal.summary.summary_prompt_builder import SummaryPromptBuilder


def test_build_prompt_with_text_replacement():
    config_prompt = """
    I have replaced {{expose_amdt}} and {{corps_amdt}} properly
    """
    explanatory_statement = "Un exposé d'amendement"
    amdt_body = "Un corps d'amendement"
    expected_prompt = """
    I have replaced Un exposé d'amendement and Un corps d'amendement properly
    """
    prompt = SummaryPromptBuilder.build_prompt_with_text_replacement(
        config_prompt=config_prompt,
        explanatory_statement=explanatory_statement,
        amdt_body=amdt_body,
    )
    assert prompt == expected_prompt
