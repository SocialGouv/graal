# Fonctionnalité d'Attribution

Lorsqu'un amendement est soumis, le système doit déterminer qui doit le réviser. Plutôt que de laisser une personne lire chaque amendement et décider manuellement, la fonctionnalité d'attribution automatise ce processus en analysant des informations spécifiques dans l'amendement.

## Prétraitement du Texte

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

## Processus d'Attribution

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

3. **Types de Matchers**
Le système dispose de trois types de matchers spécialisés, utilisés différemment selon le type de projet :

    **Pour le PLF (Projet de Loi de Finances)**
    - Correspondance par Mot-clé (sur "Exposé amdt" uniquement)
    - Correspondance par Tableau de Crédits (sur "Corps amdt original" uniquement)

    **Pour le PLFSS (Projet de Loi de Financement de la Sécurité Sociale)**
    - Correspondance par Mot-clé (sur "Exposé amdt" et "Corps amdt")
    - Correspondance par Document Juridique (sur "Corps amdt" uniquement)

    Description détaillée des matchers :

    a) **Correspondance par Tableau de Crédits**
    - Analyse les tableaux de crédits dans les amendements
    - Règles spécifiques :
      - Ignore les tableaux contenant "ligne nouvelle" ou "nouveau programme" (dans ce cas on cherche juste les mots clés dans l'exposé des motifs)
      - Attribue en fonction des programmes ayant des valeurs positives dans la colonne "-" mais pas dans la colonne "+"
      - Attribue en fonction des programmes ayant des valeurs positives dans les colonnes "+" et "-"

    b) **Correspondance par Document Juridique**
    - Recherche les références aux :
      - Codes juridiques
      - Lois spécifiques
      - Ordonnances
    - Vérifie la présence d'articles spécifiques dans ces documents

    c) **Correspondance par Mot-clé**
    - Recherche des mots-clés ou expressions spécifiques
    - Utilise une correspondance exacte des mots normalisés

4. **Sélection de l'Attribution**
   Le système :
   - Collecte toutes les correspondances des différents matchers
   - Compte la fréquence de chaque attribution proposée
   - Sélectionne l'attribution la plus fréquente
   - En cas d'égalité, choisit aléatoirement parmi les plus fréquentes
   - Si aucune correspondance n'est trouvée, utilise une attribution par défaut

5. **Traitement Parallèle**
   - Le système utilise le multiprocessing pour traiter plusieurs amendements simultanément
   - Le nombre de processus est basé sur le nombre de CPU disponibles

6. **Résultat final**
   Pour chaque amendement, le système renseigne :
   - Le nom du réviseur assigné
   - Son adresse email
   - Son service
   - Un commentaire détaillé expliquant l'affectation, incluant :
     - Le type de matcher ayant trouvé la correspondance
     - Les détails des correspondances trouvées
     - Les autres attributions possibles si pertinent

## Cas Particuliers

- **Amendements interstitiels** : Le système peut être configuré pour ne traiter que les amendements ajoutant de nouveaux articles (marqués "article add.") si nécessaire

Ce processus automatisé permet d'assurer que :

- Les amendements sont rapidement attribués aux bons réviseurs
- Le processus d'affectation est cohérent et documenté
- Chaque attribution est justifiée et traçable
- Aucun amendement ne reste sans réviseur assigné
