# Fonctionnalité de Génération de Résumé

La fonctionnalité de génération de résumé automatise la création de résumés concis et neutres pour chaque amendement. Cette automatisation permet d'obtenir rapidement une vue d'ensemble du contenu des amendements tout en garantissant une cohérence dans leur présentation.

## Prétraitement du Texte

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

## Processus de Génération

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

## Gestion des Ressources

1. **Load Balancing**
   - Distribution équilibrée des requêtes entre plusieurs clients LLM
   - Gestion des timeouts et des retries
   - Limitation du taux de requêtes par client

2. **Optimisation des Performances**
   - Traitement concurrent des amendements
   - Système de retry en cas d'échec
   - Backoff linéaire pour éviter la surcharge

## Résultat Final

Pour chaque amendement, le système produit :

- Un résumé concis et standardisé
- Une identification claire des amendements spéciaux (rédactionnels, d'appel)
- Un format cohérent facilitant la lecture et la compréhension rapide

Ce processus automatisé permet d'assurer que :

- Chaque amendement dispose d'un résumé clair et concis
- Les résumés suivent un format standardisé
- L'information essentielle est préservée tout en restant neutre
- Le traitement est rapide même pour un grand nombre d'amendements
