# Fonctionnalités de GRAAL

## Fonctionnalité d'Allotissement

La fonctionnalité d'allotissement permet d'identifier et de regrouper automatiquement les amendements identiques ou quasi-identiques. Cette fonctionnalité est particulièrement utile pour traiter efficacement les amendements déposés en plusieurs exemplaires par différents groupes parlementaires.

### Prétraitement du Texte

Avant d'analyser les amendements pour l'allotissement, le système effectue plusieurs étapes de préparation :

1. **Normalisation du texte**
   - Expansion des acronymes selon un mappage prédéfini
   - Nettoyage des textes d'amendement :
     - Suppression des phrases de "gage"
     - Normalisation des espaces et de la ponctuation

2. **Traitement des cas spéciaux**
   - Gestion des corps d'amendements vides
   - Standardisation du format des textes

### Processus de Clustering

1. **Regroupement Initial**
   Le système regroupe d'abord les amendements selon des critères de base :
   - Numéro d'article
   - Projet d'origine
   - Lecture parlementaire

2. **Analyse en Deux Étapes**

   a) **Première Étape : Clustering TF-IDF**
   - Vectorisation des textes des amendements
   - Calcul des matrices de similarité cosinus
   - Application de DBSCAN pour identifier les clusters initiaux

   b) **Seconde Étape : Raffinement**
   - Utilisation de la distance de Damerau-Levenshtein
   - Calcul des distances normalisées entre les textes
   - Second passage de DBSCAN pour affiner les clusters
   - Vérification fine des différences textuelles

3. **Filtrage des Clusters**
   - Conservation uniquement des clusters d'au moins 2 amendements

### Gestion des Amendements Allotis

1. **Sélection du Représentant**
   Pour chaque groupe d'amendements identiques :
   - Conservation d'un amendement représentatif
   - Par défaut, le premier amendement du groupe est conservé

2. **Propagation des Informations**
   Le système copie automatiquement certaines informations depuis l'amendement représentatif vers tous les amendements du groupe en fin de traitement :
   - Réponse
   - Sort
   - Commentaires
   - Objet de l'amendement
   - Avis du Gouvernement
   - Affectations (email, nom, entité)

### Optimisations et Performance

1. **Optimisation des Comparaisons**
   - Utilisation de TF-IDF pour un premier filtrage rapide
   - Application de la distance de Damerau-Levenshtein uniquement sur les groupes présélectionnés
   - Parallélisation des calculs de distance

2. **Gestion de la Mémoire**
   - Traitement par groupes d'amendements
   - Optimisation des structures de données
   - Nettoyage des données temporaires

3. **Flexibilité**
   - Seuils de similarité ajustables
   - Stratégies de sélection configurables
   - Support de différents formats d'entrée

Ce processus automatisé permet d'assurer que :

- Les amendements identiques sont rapidement identifiés et regroupés
- Le traitement est cohérent et uniforme pour tous les amendements
- Les informations sont correctement propagées au sein des groupes

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

## Fonctionnalité de Génération de Résumé

La fonctionnalité de génération de résumé automatise la création de résumés concis et neutres pour chaque amendement. Cette automatisation permet d'obtenir rapidement une vue d'ensemble du contenu des amendements tout en garantissant une cohérence dans leur présentation.

### Prétraitement du Texte

Avant de générer les résumés, le système effectue plusieurs étapes de préparation :

1. **Normalisation du texte**
   - Expansion des acronymes selon un mappage prédéfini
   - Suppression des phrases de "gage"

2. **Identification des cas spéciaux**
   Le système identifie automatiquement certains types d'amendements pour leur attribuer des résumés prédéfinis :
   - Amendements rédactionnels
     - Détectés par des phrases comme "Amendement rédactionnel" ou "correction d'erreur matérielle"
     - Résumé automatique : "Amendement rédactionnel."
   - Amendements de suppression
     - Détectés par des phrases comme "Supprimer cet article" dans le corps d'amendement
     - Résumé automatique : "Supprimer cet article."

### Processus de Génération

1. **Préparation des prompts**
   - Le système construit un prompt pour chaque amendement en combinant :
     - Le corps de l'amendement
     - L'exposé des motifs
     - Des instructions spécifiques à chaque direction pour la génération du résumé

2. **Règles de génération**
   Pour la plupart des directions, les règles pour la génération des résumés sont les suivantes :

   a) **Règles de structure**
   - Commencer par un verbe à l'infinitif
   - Longueur limitée (8 à 20 mots)
   - Cas spéciaux :
     - Commencer par "Remettre un rapport" pour les amendements demandant un rapport
     - Commencer par "Expérimenter" pour les amendements d'expérimentation

   b) **Règles de contenu**
   - Inclure les informations essentielles :
     - Acteurs et bénéficiaires concernés
     - Lieux d'application si spécifiés
     - Critères d'application
     - Étapes multiples si présentes
   - Inclure les taux mais pas les autres chiffres
   - Utiliser les acronymes sans les expliciter

   c) **Règles de style**
   - Maintenir une neutralité politique
   - Éviter les adjectifs
   - Ne pas inclure de justifications
   - Ne pas répéter le contexte
   - Ne pas ajouter de notes ou d'explications

3. **Génération et optimisation**
   - Utilisation d'un système de load balancing pour distribuer les requêtes entre plusieurs clients LLM
   - Vérification de la longueur des résumés générés
   - Nouvelle génération automatique si le résumé dépasse 25 mots

4. **Post-traitement**
   - Identification des amendements d'appel
     - Ajout du préfixe "APPEL : " au résumé si l'exposé contient "amendement d'appel"
     - Exception pour les amendements de suppression

### Gestion des Ressources

1. **Load Balancing**
   - Distribution équilibrée des requêtes entre plusieurs clients LLM
   - Gestion des timeouts et des retries
   - Limitation du taux de requêtes par client

2. **Optimisation des Performances**
   - Traitement concurrent des amendements
   - Système de retry en cas d'échec
   - Backoff linéaire pour éviter la surcharge

### Résultat Final

Pour chaque amendement, le système produit :

- Un résumé concis et standardisé
- Une identification claire des amendements spéciaux (rédactionnels, d'appel)
- Un format cohérent facilitant la lecture et la compréhension rapide

Ce processus automatisé permet d'assurer que :

- Chaque amendement dispose d'un résumé clair et concis
- Les résumés suivent un format standardisé
- L'information essentielle est préservée tout en restant neutre
- Le traitement est rapide même pour un grand nombre d'amendements

## Fonctionnalité de Recherche de Similarités

La fonctionnalité de recherche de similarités permet d'identifier automatiquement les amendements similaires entre différentes lectures d'un projet de loi. Cette fonctionnalité se décompose en deux parties principales : la construction d'une base de données d'amendements historiques et la recherche de similarités avec les nouveaux amendements.

### Construction de la Base de Données

1. **Chargement des Données**
   - Chargement des amendements depuis des fichiers JSON et Excel
   - Possibilité de filtrer par projet (ex: PLFSS, PLACSS)
   - Support de plusieurs lectures et organes parlementaires

2. **Prétraitement des Amendements**
   - Expansion des acronymes selon un mappage prédéfini
   - Suppression des phrases de "gage"
   - Normalisation des espaces et de la ponctuation
   - Remplacement des corps d'amendements vides par un texte standard

3. **Optimisation de la Base**
   - Regroupement des amendements par :
     - Lecture
     - Projet d'origine
     - Numéro d'article
   - Filtrage des doublons en conservant :
     - L'amendement le plus récent
     - L'amendement avec une réponse (prioritaire sur ceux sans réponse)

4. **Sauvegarde**
   - Stockage des amendements prétraités dans un fichier pickle
   - Conservation des métadonnées essentielles (projet, lecture, réponses)

### Processus de Recherche de Similarités

1. **Prétraitement**
   - Application des mêmes règles de normalisation aux nouveaux amendements
   - Filtrage des amendements vides ou incomplets

2. **Clustering Initial**
   Le système utilise une approche en deux étapes pour identifier les similarités :

   a) **Pré-filtrage par TF-IDF**
    TF-IDF (Term Frequency-Inverse Document Frequency) est une méthode utilisée pour évaluer l'importance d'un mot dans un document par rapport à un ensemble de documents. Le principe est que plus un mot est rare dans l'ensemble des documents, plus il est significatif et son score est élevé.

   - Vectorisation des textes (corps et exposés) : Chaque document est représenté par un vecteur où chaque dimension correspond à un mot du vocabulaire, et la valeur dans chaque dimension est le score TF-IDF du mot dans le document
   - Calcul des similarités cosinus : Détermine le degré de similarité entre les vecteurs de 2 documents. Plus les vecteurs sont proches, plus les documents sont similaires
   - Création de clusters d'amendements potentiellement similaires
   - Optimisation par regroupement selon :
     - Le numéro d'article
     - Le projet d'origine

   b) **Comparaison Fine**
   - Utilisation de la distance de Damerau-Levenshtein : mesure le nombre de lettres qui diffèrent entre deux textes
   - Calcul d'un ratio de similarité précis
   - Application de seuils de similarité différents selon le type d'amendement

3. **Règles de Correspondance**
   Le système applique différents seuils de similarité :
   - Seuil par défaut pour le clustering (0.4)
   - Seuils spécifiques pour certains types d'amendements :
     - Amendements rédactionnels (0.95)
     - Corps d'amendements (0.9)
     - Exposés des motifs (0.4)

4. **Filtrage Contextuel**
   - Possibilité de filtrer les comparaisons par projet et par article pour une comparaison plus pertinente

### Résultat Final

Pour chaque amendement similaire trouvé, le système :

1. **Copie les Informations Pertinentes**
   - La réponse de l'amendement historique
   - Le sort (s'il contient "irrecevable")

2. **Ajoute des Métadonnées**
   Dans les commentaires sont ajoutés :
   - Le projet d'origine
   - Le numéro d'amendement source
   - La lecture concernée
   - L'organe parlementaire
   - La colonne utilisée pour la comparaison (corps ou exposé)
   - Le sort copié (si applicable)

### Optimisations et Performance

1. **Optimisation des Comparaisons**
   - Utilisation de TF-IDF pour un pré-filtrage rapide
   - Comparaisons détaillées uniquement sur les clusters pertinents
   - Regroupement par article pour réduire l'espace de recherche

2. **Gestion de la Mémoire**
   - Traitement par groupes d'amendements
   - Stockage optimisé des données historiques
   - Nettoyage des données redondantes

3. **Flexibilité**
   - Seuils ajustables selon les besoins
   - Filtres configurables par projet
   - Support de différents formats d'entrée (JSON, Excel)

Ce processus automatisé permet d'assurer que :

- Les amendements similaires sont rapidement identifiés
- Les réponses pertinentes sont réutilisées
- Le traitement est optimisé pour de grands volumes d'amendements
- La traçabilité des correspondances est maintenue
