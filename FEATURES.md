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
