import textwrap

from amendements_intelligents.types import Prompt, TxtContent


class SummaryPromptBuilder:
    @staticmethod
    def build_prompt(
        explanatory_statement: TxtContent, amdt_body: TxtContent
    ) -> Prompt:
        prompt = f"""
Contexte : Tu es un juriste spécialisé dans le droit de la sécurité sociale en France. Ta tâche est de résumer un amendement et de rester politiquement correct.

Instruction: Résume l'amendement en français en une phrase courte (de 8 à 18 mots). Le résumé doit être concis, neutre, commencer par un verbe à l'infinitif, inclure les taux pour la clareté (mais pas d'autres chiffres), ne pas inventer de chiffres qui ne figurent pas dans l'amendement, ne pas utiliser d'adjectifs. Exclus les justifications de l'amendement. Ne répète pas le contexte. Utilise des acronymes, sans les expliciter. Si l'amendement concerne un rapport, commence ta réponse par "Remettre un rapport". N'ajoute pas de notes expliquant le résumé. Ne soit pas trop technique.

Aide-toi du corps de l'amendement qui sera fourni pour extraire des informations pertinentes mais l'exposé de l'amendement est le plus important.

Exemples :

- Exposé de l'amendement :
Cet amendement vise à mettre fin à une situation soumettant à des cotisations forfaitaires les chefs d’exploitation agricole ou d’entreprise agricole bénéficiaires du RSA. Il les soustrait ainsi au paiement des cotisations accidents du travail, invalidité des conjoints collaborateurs et de la cotisation forfaitaire due au titre des indemnités journalières maladie.
Face à la situation de détresse de nombreux agriculteurs, cet amendement vise à permettre à ceux en situation de grande précarité d’être soulagés du paiement de cotisations qui viennent renforcer les difficultés financières dans lesquels ceux-ci peuvent se trouver.
Il serait ainsi mis fin à une situation juridique instable où nombre d’agriculteurs se voient réclamés par la mutualité sociale agricole des cotisations sociales forfaitaires qu’ils ne sont pas en mesure de payer.

Résumé :
Exonérer de toute cotisation forfaitaire les exploitants agricoles bénéficiaires du revenu de solidarité active

- Exposé de l'amendement :
Demande de rapport du Gouvernement au Parlement sur le financement de la sécurité sociale à Mayotte et l’opportunité d’une accélération de la trajectoire de convergence des cotisations et contributions sociales.

Résumé :
Remettre un rapport au Parlement sur le financement de la sécurité sociale à Mayotte et la convergence des cotisations sociales.

Voici l'amendement que tu dois résumer :

Corps de l'amendement :
{amdt_body}

Exposé de l'amendement :
{explanatory_statement}

Résumé :
"""

        return textwrap.dedent(prompt).strip()
