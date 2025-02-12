# Fonctionnalité d'Allotissement

La fonctionnalité d'allotissement permet d'identifier et de regrouper automatiquement les amendements identiques ou quasi-identiques. Cette fonctionnalité est particulièrement utile pour traiter efficacement les amendements déposés en plusieurs exemplaires par différents groupes parlementaires.

## Prétraitement du Texte

Avant d'analyser les amendements pour l'allotissement, le système effectue plusieurs étapes de préparation :

1. **Normalisation du texte**
   - Expansion des acronymes selon un mappage prédéfini
   - Nettoyage des textes d'amendement :
     - Suppression des phrases de "gage"
     - Normalisation des espaces et de la ponctuation

2. **Traitement des cas spéciaux**
   - Gestion des corps d'amendements vides
   - Standardisation du format des textes

## Processus de Clustering

1. **Regroupement Initial**
   Le système regroupe d'abord les amendements selon des critères de base :
   - Numéro d'article
   - Projet d'origine
   - Lecture parlementaire

2. **Analyse de Similarité**

   Le système utilise une approche de clustering avec un seuil de similarité très strict (0.0001) pour identifier les amendements identiques ou quasi-identiques. Cette analyse est effectuée sur le corps des amendements uniquement, après normalisation et nettoyage du texte.

   Le processus se déroule en deux phases :
   - Une première phase de clustering pour identifier les groupes initiaux
   - Une phase de raffinement qui vérifie la similarité au sein des groupes identifiés

## Gestion des Amendements Allotis

1. **Sélection du Représentant**
   Pour chaque groupe d'amendements identiques :
   - Conservation d'un amendement représentatif selon une stratégie configurable
   - Par défaut, le premier amendement du groupe est conservé
   - En cas d'attribution activée, priorité aux amendements avec des attributions non par défaut

2. **Propagation des Informations**
   Le système copie automatiquement les informations suivantes depuis l'amendement représentatif vers tous les amendements du groupe :
   - Réponse
   - Sort
   - Commentaires
   - Objet de l'amendement
   - Avis du Gouvernement
   - Affectation (email)
   - Affectation (nom)
   - Entité Pilote

   Note : L'amendement source pour la propagation est celui qui contient le plus de champs non-vides parmi ces informations.

## Optimisations et Performance

1. **Optimisation et Performance**
   - Utilisation d'un seuil de similarité strict pour une identification précise
   - Traitement par groupes d'amendements selon leur numéro d'article
   - Prétraitement efficace des textes pour normalisation

2. **Flexibilité**
   - Stratégie de sélection du représentant configurable via une fonction personnalisable
   - Support de différents formats d'entrée (JSON, Excel)
   - Intégration avec d'autres fonctionnalités comme l'attribution

Ce processus automatisé permet d'assurer que :

- Les amendements identiques sont rapidement identifiés et regroupés
- Le traitement est cohérent et uniforme pour tous les amendements
- Les informations sont correctement propagées au sein des groupes
