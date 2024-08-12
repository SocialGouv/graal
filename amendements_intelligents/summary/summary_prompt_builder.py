from amendements_intelligents.types import Prompt, TxtContent


class SummaryPromptBuilder:
    @staticmethod
    def build_prompt(explanatory_statement: TxtContent, body: TxtContent) -> Prompt:
        prompt = f"""Contexte : Tu es un juriste spécialisé dans le droit de la sécurité sociale en France. Ta tâche est de résumer un amendement et de rester politiquement correct.

        Instruction: Résume l'amendement en français en une phrase courte (de 8 à 18 mots). Le résumé doit être concis, neutre, commencer par un verbe à l'infinitif, inclure les taux lorsqu'on est sûr qu'ils sont applicables (mais pas d'autres chiffres), ne pas inventer de chiffres qui ne figurent pas dans l'amendement, ne pas utiliser d'adjectifs, et exclure les justifications de l'amendement. Ne répète pas le contexte. Utilise des acronymes, sans les expliciter. Si l'amendement concerne un rapport, commence ta réponse par "Remettre un rapport sur...". N'ajoute pas de notes expliquant le résumé.

        Exemples :

        ```
        Amendement :
        Cet amendement vise à mettre fin à une situation soumettant à des cotisations forfaitaires les chefs d’exploitation agricole ou d’entreprise agricole bénéficiaires du RSA. Il les soustrait ainsi au paiement des cotisations accidents du travail, invalidité des conjoints collaborateurs et de la cotisation forfaitaire due au titre des indemnités journalières maladie.
        Face à la situation de détresse de nombreux agriculteurs, cet amendement vise à permettre à ceux en situation de grande précarité d’être soulagés du paiement de cotisations qui viennent renforcer les difficultés financières dans lesquels ceux-ci peuvent se trouver.
        Il serait ainsi mis fin à une situation juridique instable où nombre d’agriculteurs se voient réclamés par la mutualité sociale agricole des cotisations sociales forfaitaires qu’ils ne sont pas en mesure de payer.

        Résumé :
        Exonérer de toute cotisation forfaitaire les exploitants agricoles bénéficiaire du revenu de solidarité active


        Amendement :
        Demande de rapport du Gouvernement au Parlement sur le financement de la sécurité sociale à Mayotte et l’opportunité d’une accélération de la trajectoire de convergence des cotisations et contributions sociales.

        Résumé :
        Remettre un rapport sur le financement de la sécurité sociale à Mayotte et la convergence des cotisations sociales.

        Amendement :
        Cette disposition est destinée à mieux prendre en compte, au titre de la retraite, la pénibilité à laquelle sont exposés les agents contractuels de la fonction publique. Aujourd’hui, un fonctionnaire qui a commencé sa carrière en tant que contractuel sur des fonctions équivalentes à celles d’un agent titulaire relevant de la catégorie active ne peut en effet pas les valoriser au moment de son départ à la retraite pour la comptabilisation de la durée de services requise pour bénéficier du droit au départ anticipé. Or, il apparaît que les trajectoires professionnelles des agents titulaires débutent de plus en plus fréquemment par des périodes contractuelles.
        Avec la mesure proposée, le présent amendement prévoit que les périodes effectuées sur des emplois actifs ou super-actifs comme agents contractuels seront, lorsque les agents concernés seront titularisés, prises en compte dans la limite de 10 ans pour le décompte de la condition de durée en services actifs (17 ans) ou super actifs (27 ans en général) à remplir pour bénéficier d’un droit au départ anticipé.
        Cette mesure est indispensable pour améliorer les droits à retraite des agents publics ayant eu une première partie de carrière en tant que contractuel et ayant exercé des métiers pénibles, notamment au sein de la fonction publique hospitalière.

        Résumé :
        Prise en compte des services de contractuels dans les services actifs des titularisés

        Amendement :
        L’article 23 du projet de loi de financement de la sécurité sociale pour 2024 porte une réforme importante tendant à inscrire dans le droit commun un grand nombre de dispositifs expérimentaux lancés sur le fondement de l’article L. 162-31-1 du code de la sécurité sociale (dit « article 51 »).Cet élan d’innovations organisationnelles mérite d’être soutenu, la FHP SMR portant elle-même un tel projet au niveau national intitulé « inspir’action » et visant les patients atteints de BPCO. Pour autant, l’objectif doit viser à améliorer les parcours de certains patients, en recourant de façon graduée et complémentaire aux différents acteurs de l’offre de soins, afin de leur apporter une pertinence de prise en charge en lien avec leurs besoins. Il ne saurait aboutir à déstabiliser l’offre de soins participant déjà à la prise en charge de ces mêmes patients, et notamment les soins médicaux et de réadaptation spécialisés dans les actions coordonnées de prévention autour d’une équipe pluridisciplinaire, et entrainer in fine une perte de chance pour le patient.C’est donc la complémentarité entre l’offre de soins territoriale existante et le dispositif expérimental en voie de pérennisation, qui doit être recherchée dans chaque territoire. C’est pourquoi le présent amendement proposer de mieux coordonner les différents acteurs autour de ces parcours et de renforcer les équilibres locaux de chaque filière d’offre de soins régionale.

        Résumé :
        Prendre en compte l’organisation territoriale de l’offre de soins dans chaque région dans le déploiement des parcours coordonnés renforcés
        ```

        Aide-toi aussi du corps de l'amendement qui sera fourni après la balise `Corps de l'amendement` pour extraire des informations pertinentes pour le résumé.

        Amendement :
        {explanatory_statement}

        Corps de l'amendement :
        {body}

        Résumé :
        """

        return prompt
