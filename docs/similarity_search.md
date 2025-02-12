# Fonctionnalité de Recherche de Similarités

La fonctionnalité de recherche de similarités permet d'identifier automatiquement les amendements similaires entre différentes lectures d'un projet de loi. Cette fonctionnalité se décompose en deux parties principales : la construction d'une base de données d'amendements historiques et la recherche de similarités avec les nouveaux amendements.

## Construction de la Base de Données

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

## Processus de Recherche de Similarités

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

## Résultat Final

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

## Optimisations et Performance

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
