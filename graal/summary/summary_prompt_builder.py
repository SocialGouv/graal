import textwrap

from graal.custom_types import Prompt, TxtContent


class SummaryPromptBuilder:
    @staticmethod
    def build_prompt_with_text_replacement(
        config_prompt: Prompt, explanatory_statement: TxtContent, amdt_body: TxtContent
    ) -> Prompt:
        config_prompt = config_prompt.replace("{{expose_amdt}}", explanatory_statement)
        config_prompt = config_prompt.replace("{{corps_amdt}}", amdt_body)
        return config_prompt

    @staticmethod
    def build_prompt_summarize_again(current_summary: TxtContent) -> Prompt:
        prompt = f"""
Contexte :
Ta tâche est de résumer un texte.

Le résumé doit suivre ces règles strictes :
1. Si le texte concerne une expérimentation, commence le résumé par "Expérimenter", suivi du sujet de l'expérimentation.
2. N'écrire que le résumé, sans ajouter de notes ou d'explications.
3. Préserver au maximum les informations importantes.
5. Si le texte concerne un rapport, commence le résumé par "Remettre un rapport".
6. Commencer par un verbe à l'infinitif.
7. Être concis (8 à 20 mots).

Texte à résumer :
{current_summary}

Résumé :
"""
        return textwrap.dedent(prompt).strip()
