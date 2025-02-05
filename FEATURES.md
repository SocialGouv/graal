# Fonctionnalités de GRAAL

## Fonctionnalité d'Attribution

Lorsqu'un amendement est soumis, le système doit déterminer qui doit le réviser. Plutôt que de laisser une personne lire chaque amendement et décider manuellement, la fonctionnalité d'attribution automatise ce processus en analysant des informations spécifiques dans l'amendement.

### Prétraitement du Texte

Avant d'analyser les amendements, le système normalise tout le texte afin d'assurer une correspondance cohérente. Cela comprend :

1. **Normalisation du texte de l'amendement**
   - Expansion des acronymes selon un mappage prédéfini
        - Exemple : "CSS" devient "code de la sécurité sociale"
   - Suppression des accents et des caractères spéciaux
        - Exemple : "sécurité" devient "securite"
   - Conversion de tout le texte en minuscules
        - Exemple : "Code de la Santé" devient "code de la sante"
   - Suppression des espaces et sauts de ligne superflus
        - Exemple : "article&nbsp;&nbsp;123\n&nbsp;&nbsp;du&nbsp;&nbsp;&nbsp;code" devient "article 123 du code"

2. **Normalisation des mots-clés**
   - Application des mêmes règles de normalisation et d'expansion des acronymes que pour les amendements

3. **Nettoyage des références**
   - Standardisation des références aux articles
        - Exemple : "Art. L. 123-4" et "article L123-4" sont traités de manière identique
   - Suppression des phrases de "gage" (textes juridiques standards n'affectant pas l'attribution)
        - Exemple : Suppression des phrases commençant par "la perte de recettes" ou "la charge pour l'état"

### Processus d'Attribution

1. **Chargement des données de référence**
   - Le système charge des informations depuis une feuille de configuration contenant :
     - Listes de codes juridiques (ex. "Code de la sécurité sociale")
     - Listes de lois et d'ordonnances spécifiques
     - Listes d'articles dans ces codes et lois
     - Mots-clés associés aux différents réviseurs
     - Affectations par défaut en cas d'absence de correspondance claire
     - Coordonnées (email, service) de chaque réviseur

2. **Analyse du texte**
   Le système examine deux parties principales de chaque amendement :
   - Le texte principal ("Corps amdt")
   - Le texte explicatif ("Exposé amdt")

3. **Recherche des correspondances**
   Le système recherche quatre types de correspondances dans le texte de l'amendement :

   a) **Références aux codes**
   - Recherche de mentions de codes juridiques spécifiques
   - Exemple : "code de la sécurité sociale" ou "code du travail"

   b) **Références aux lois**
   - Identification des références à des lois spécifiques
   - Exemple : "loi n° 2023-XXX du 1er janvier 2023"

   c) **Références aux ordonnances**
   - Identification des références à des ordonnances spécifiques
   - Exemple : "ordonnance n° 2023-XXX du 1er janvier 2023"

   d) **Mots-clés**
   - Recherche de termes ou expressions spécifiques indiquant certains sujets
   - Ces mots-clés sont associés à des réviseurs en fonction de leur expertise

4. **Affectation**
   Le système :
   - Collecte toutes les correspondances potentielles trouvées dans le texte
   - Si plusieurs correspondances sont détectées :
     - Enregistre toutes les correspondances possibles dans les commentaires
     - Sélectionne aléatoirement un réviseur qualifié
   - Si aucune correspondance n'est trouvée :
     - Attribue l'amendement à une personne issue d'une liste de réviseurs par défaut
     - Ajoute une note dans les commentaires indiquant qu'il s'agit d'une affectation par défaut

5. **Résultat final**
   Pour chaque amendement, le système renseigne :
   - Le nom du réviseur assigné
   - Son adresse email
   - Son service
   - Un commentaire expliquant l'affectation

### Cas Particuliers

- **Correspondances multiples** : Si un amendement peut être attribué à plusieurs personnes (par exemple, s'il mentionne plusieurs codes juridiques), le système :
  - Choisit une personne aléatoirement parmi les réviseurs qualifiés
  - Enregistre les autres réviseurs possibles dans la section commentaires
  - Cela permet une transparence et une réattribution facile si nécessaire

- **Aucune correspondance** : Si le système ne trouve aucun résultat clair, il :
  - Assigne l'amendement à une personne issue d'une liste de réviseurs par défaut
  - Ajoute une note dans les commentaires précisant qu'il s'agit d'une affectation par défaut

- **Amendements interstitiels** : Le système peut être configuré pour ne traiter que les amendements ajoutant de nouveaux articles (marqués "article add.") si nécessaire

Ce processus automatisé permet d'assurer que :

- Les amendements sont rapidement attribués aux bons réviseurs
- Le processus d'affectation est cohérent et documenté
- Chaque attribution est justifiée et traçable
- Aucun amendement ne reste sans réviseur assigné
