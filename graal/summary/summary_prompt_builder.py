import textwrap

from graal.custom_types import Prompt, TxtContent


class SummaryPromptBuilder:
    @staticmethod
    def build_prompt(
        explanatory_statement: TxtContent, amdt_body: TxtContent
    ) -> Prompt:
        prompt = f"""
Contexte :
Tu es un juriste spécialisé en droit de la sécurité sociale en France. Ta tâche est de résumer un amendement en respectant une neutralité politique.

Instructions :

Le résumé doit suivre ces règles strictes :
1. Si l'amendement concerne un rapport, commence ta réponse par "Remettre un rapport".
2. Si l'amendement concerne une expérimentation, commence ta réponse par "Expérimenter", suivi du sujet de l'expérimentation.
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
15. Préciser les critères d'application de l'amendement.
16. Être écrit en français.
17. Être concis (8 à 20 mots).

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

    @staticmethod
    def build_prompt_summarize_again(current_summary: TxtContent) -> Prompt:
        prompt = f"""
Contexte :
Tu es un juriste spécialisé en droit de la sécurité sociale en France. Ta tâche est de résumer un texte.

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
