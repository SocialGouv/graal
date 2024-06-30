import time

import ollama
from ollama import Options

from amendements_intelligents.types import Prompt, TxtContent


class SummaryGeneratorOllamaClient:
    def __init__(self):
        self.client = ollama.Client(host="http://localhost:11434/v1")
        self.MAX_RETRIES = 3

    def build_prompt(self, content: TxtContent):
        prompt = f"""
        Contexte : Tu es un juriste qui doit resumer un amendement. Ta tache est de resumer l'amendement en 1 phrase maximum.

        Instruction : Resume l'amendement en français. Le résumé doit être neutre, il doit commencer par un verbe à l'infinitif, conserver un vocabulaire juridique et les chiffres importants.

        Donnée d'entrée :
        Voici le texte de l'amendement :
        {content}

        Résumé de l'amendement :
        """

        return prompt

    def build_prompt_experimental(self, content: TxtContent):
        prompt = f"""
        Contexte : Tu es un juriste spécialisé dans le droit de la sécurité sociale en France. Ta tâche est de résumer un amendement.

        Instruction : Résume l'amendement en français et en une seule phrase. Ce résumé doit être concis, neutre, et commencer par un verbe à l'infinitif. Il doit conserver un vocabulaire juridique précis et inclure les chiffres et informations importantes.

        Exemples :

        ```
        Amendement :
        Le gouvernement s’est montré favorable à cet amendement lors de son audition en Commission des affaires sociales le 11 octobre 2023 de sorte à permettre la levée du gage et assurer sa recevabilité financière.
        L’amendement de Michel Creton permet de maintenir des jeunes en IME faute de place . Ce dispositif adapté a aujourd’hui plus de 30 ans. Or cette solution qui a été salvatrice pour de nombreux jeunes et leur famille n’a pas vocation à s’inscrire dans la durée. Pour autant, faute de place et de dispositif adapté ce qui devait n’être que temporaire est devenu durable.
        Ainsi, il s’agit aujourd’hui de porter une véritable solution vers une société plus inclusive. Une personne en situation de handicap est une personne avant tout. Il importe de considérer que cette personne est un citoyen à part entière avec des besoins spécifiques, mais également des envies, des aspirations, des appétences et des compétences qui se dévoilent parfois dans une temporalité différée. La solution se trouve dans la construction collective d’une société où chaque personne, quelle que soit sa situation, doit trouver sa place et un emploi qui correspond à ses besoins et ses aspirations, évoluer dans son parcours professionnel et participer à la vie économique de notre pays.
        Cet amendement dit « Melvin - Tremplin » proposé par l’Adapei des Hautes-Pyrénées, est soutenu par l’Unapei. Il vise à ce que l’accueil par un dispositif transitoire à destination des jeunes, dès 16 ans, en partenariat avec les agences régionales de santé et les conseils départementaux soit systématiquement étudié et proposé par les commissions des droits et de l'autonomie des personnes en situation de handicap.
        Résumé :
        Elargir les compétences de la commission des droits et de l'autonomie des personnes handicapées (CDAPH) des MDPH à l'orientation vers des dispositifs de transition à 16 ans.

        Amendement :
        Cet amendement vise à mettre fin à une situation soumettant à des cotisations forfaitaires les chefs d’exploitation agricole ou d’entreprise agricole bénéficiaires du RSA. Il les soustrait ainsi au paiement des cotisations accidents du travail, invalidité des conjoints collaborateurs et de la cotisation forfaitaire due au titre des indemnités journalières maladie.
        Face à la situation de détresse de nombreux agriculteurs, cet amendement vise à permettre à ceux en situation de grande précarité d’être soulagés du paiement de cotisations qui viennent renforcer les difficultés financières dans lesquels ceux-ci peuvent se trouver.
        Il serait ainsi mis fin à une situation juridique instable où nombre d’agriculteurs se voient réclamés par la mutualité sociale agricole des cotisations sociales forfaitaires qu’ils ne sont pas en mesure de payer.
        Résumé :
        Exonérer de toute cotisation forfaitaire les exploitants agricoles bénéficiaire du revenu de solidarité active

        Amendement :
        Demande de rapport du Gouvernement au Parlement sur le financement de la sécurité sociale à Mayotte et l’opportunité d’une accélération de la trajectoire de convergence des cotisations et contributions sociales.
        Résumé :
        Demander un rapport sur le financement de la sécurité sociale à Mayotte et la convergence des cotisations sociales.
        ```

        Donnée d'entrée :

        Amendement :
        {content}

        Résumé :

        """

        return prompt

    def generate_response(self, prompt: Prompt):
        for i in range(self.MAX_RETRIES):
            try:
                result = self.client.generate(
                    model="llama3",
                    prompt=prompt,
                    stream=False,
                    options=Options(temperature=0),
                )
                return result["response"]
            except ollama._types.ResponseError as e:
                if "no slots available" in str(e):
                    time.sleep(2**i)  # exponential backoff
                else:
                    raise  # re-raise the exception if it's not a "no slots available" error
        raise Exception(
            f"Failed to generate an answer after {self.MAX_RETRIES} retries"
        )
