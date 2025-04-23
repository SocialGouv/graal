# Fonctionnalité de Détection des Similarités

La fonctionnalité de détection des similarités permet d'identifier les amendements similaires et d'ajouter des informations sur ces similarités dans les commentaires des amendements. Contrairement à l'allotissement qui filtre les amendements similaires, cette fonctionnalité conserve tous les amendements et enrichit leurs métadonnées.

## Processus de Détection

1. **Prétraitement du Texte**
   - Normalisation des textes d'amendement (comme pour l'allotissement)
   - Suppression des phrases de "gage"
   - Normalisation des espaces et de la ponctuation

2. **Clustering et Calcul de Similarité**
   - Utilisation de TF-IDF et DBSCAN pour identifier les groupes initiaux
   - Raffinement avec la distance de Damerau-Levenshtein
   - Calcul des pourcentages de similarité entre amendements dans chaque cluster

3. **Enrichissement des Commentaires**
   - Pour chaque amendement, ajout d'une ligne dans la colonne "Commentaires" listant les amendements similaires avec leurs pourcentages de similarité
   - Format: "Amdt similaires : 102 (86%), 103 (42%)"

## Configuration

La fonctionnalité peut être configurée via le fichier `config/default.json` avec les options suivantes :

```json
{
    "similarities_within_lectures": {
        "enabled": true,
        "column": "Corps amdt",
        "similarity_threshold": 0.8
    }
}
```

### Options de Configuration

- **similarities_within_lectures.enabled** : Active ou désactive la fonctionnalité
- **similarities_within_lectures.column** : Colonne utilisée pour l'analyse de similarité (valeur par défaut : "Corps amdt")
- **similarities_within_lectures.similarity_threshold** : Seuil de similarité en pourcentage (de 0.0 à 1.0, où 1.0 signifie 100% similaire). Seuls les amendements dont la similarité est supérieure ou égale à ce seuil seront inclus dans les commentaires.

## Différences avec l'Allotissement

Contrairement à la fonctionnalité d'allotissement qui filtre les amendements pour n'en conserver qu'un seul par groupe, la détection des similarités conserve tous les amendements et ajoute simplement des informations sur les similarités dans les commentaires. Cela permet de :

1. Informer les utilisateurs des amendements similaires
1. Fournir une indication du degré de similarité entre les amendements

Les deux fonctionnalités peuvent être utilisées simultanément dans le pipeline.
