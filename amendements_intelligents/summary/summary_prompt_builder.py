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

    @staticmethod
    def build_prompt_new(
        explanatory_statement: TxtContent, amdt_body: TxtContent
    ) -> Prompt:
        prompt = f"""
Contexte :
Tu es un juriste spécialisé en droit de la sécurité sociale en France. Ta tâche est de résumer un amendement en respectant une neutralité politique.

Instructions :

Le résumé doit suivre ces règles strictes :
1. Être écrit en français.
2. Être concis (8 à 20 mots).
3. Commencer par un verbe à l'infinitif.
4. Être neutre.
5. Ne pas utiliser d'adjectifs.
6. Ne pas répéter le contexte.
7. Ne pas ajouter de notes ou d'explications.
8. Inclure les taux, mais pas d'autres chiffres.
9. Utiliser des acronymes sans les expliciter.
10. Préciser les acteurs et bénéficiaires de l'amendement (exemples : "Calculer les cotisations des chefs d'exploitation...", "Autoriser les travailleurs indépendants à se verser une prime...").
11. Préciser les lieux concernés par l'amendement (exemple : "Placer les entreprises de Guadeloupe, de Martinique et de La Réunion du BTP dans le barème renforcé.").
12. Faire apparaître toutes les étapes proposées (exemple : "Réduire le taux de cotisations d'assurance maladie de 4 points à 1,6 SMIC puis de 2 points à compter de 2025.").
13. Exclure les justifications de l'amendement.
14. Préciser le fond de l'amendement.
15. Préciser les conditions de les critères d'application de l'amendement.
16. Si l'amendement concerne un rapport, commence ta réponse par "Remettre un rapport"

Utilise principalement l'exposé de l'amendement pour extraire les informations pertinentes, mais tu peux également t'appuyer sur le corps de l'amendement.

Exemples :

**Exemple 1 :**

*Exposé de l'amendement :*
Plutôt que de doubler les franchises médicales sur les médicaments et les consultations, avec une perspective de recettes d’à peine 800 millions d’euros, le Gouvernement devrait rétablir le principe de compensation systématique et intégrale des exonérations de cotisations sociales nouvelles.
Cet amendement vise donc à limiter la mise en place de nouveaux dispositifs d’exonérations de cotisations sociales en prévoyant que chaque nouveau dispositif fasse l’objet de la suppression d’un dispositif existant pour un montant équivalent.

*Résumé :*
Compenser par suppression en cas de nouvelle exonération.

**Exemple 2 :**

*Exposé de l'amendement :*
Demande de rapport du Gouvernement au Parlement sur le financement de la sécurité sociale à Mayotte et l’opportunité d’une accélération de la trajectoire de convergence des cotisations et contributions sociales.

*Résumé :*
Remettre un rapport au Parlement sur le financement de la sécurité sociale à Mayotte et la convergence des cotisations sociales.

**Amendement à résumer :**

*Corps de l'amendement :*
{amdt_body}

*Exposé de l'amendement :*
{explanatory_statement}

Résumé :
"""

        return textwrap.dedent(prompt).strip()
