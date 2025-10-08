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

   Le système utilise une approche de clustering avec des seuils de similarité configurables pour identifier les amendements identiques ou quasi-identiques. Cette analyse est effectuée sur la colonne spécifiée dans la configuration (par défaut "Corps amdt"), après normalisation et nettoyage du texte.

   Le processus se déroule en deux phases :
   - Une première phase de clustering TF-IDF pour identifier les groupes initiaux, utilisant le seuil `tf_idf_threshold` (configurable dans le fichier de configuration)
   - Une phase de raffinement qui vérifie la similarité au sein des groupes identifiés en utilisant la distance de Damerau-Levenshtein avec le seuil `similarity_threshold` (également configurable)

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

## Configuration

La fonctionnalité d'allotissement peut être configurée via le fichier `config/default.json` avec les options suivantes :

```json
{
    "tf_idf_threshold": 0.4,
    "allotments": {
        "enabled": true,
        "column": "Corps amdt",
        "similarity_threshold": 0.999
    }
}
```

### Options de Configuration

- **tf_idf_threshold** : Seuil pour le clustering TF-IDF initial (valeur par défaut : 40%)
- **allotments.enabled** : Active ou désactive la fonctionnalité d'allotissement
- **allotments.column** : Colonne utilisée pour l'analyse de similarité (valeur par défaut : "Corps amdt")
- **allotments.similarity_threshold** : Seuil de similarité pour la distance de Damerau-Levenshtein (valeur par défaut : 0.999)

Un seuil plus élevé pour `tf_idf_threshold` (par exemple 0.4) permet d'identifier des groupes d'amendements plus larges lors de la phase initiale, tandis qu'un seuil plus bas pour `similarity_threshold` (par exemple 0.999) assure que seuls les amendements très similaires sont regroupés lors de la phase de raffinement.
