# GRAAL API Documentation

## Core Endpoints

### 1. Allotment Endpoint

**Endpoint:** `/api/allotment`

**Method:** POST

**Description:** Groups amendments by similarity based on configured parameters.

**Request Body:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      "Groupe": "Group name",
      "mission_titre_court": "mission title"
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "column": "Corps amdt",
    "similarity_threshold": 0.9999,
    "group_by_columns": ["Num article"],
    "clustering_similarity_threshold": 0.4
  }
}
```

**Response:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      "Allotissement": [1, 2, 4],
      // Other amendment fields
    }
    // More amendments
  ],
}
```

**Configuration Parameters:**

| Parameter                       | Type   | Required | Description                                                       |
| ------------------------------- | ------ | -------- | ----------------------------------------------------------------- |
| column                          | string | Yes      | Column used for similarity comparison (e.g., "Corps amdt")        |
| similarity_threshold            | float  | Yes      | Threshold above which amendments are considered similar (0.0-1.0) |
| group_by_columns                | array  | No       | Columns to group by before comparing (e.g., ["Num article"])      |
| clustering_similarity_threshold | float  | No       | TF-IDF threshold for clustering (default: 0.4)                    |

### 2. Summary Generation Endpoint

**Endpoint:** `/api/summary`

**Method:** POST

**Description:** Generates summaries for amendments using a language model.

**Request Body:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "summary_column": "Objet amdt",
    "should_overwrite": true,
    "llm_config": {
    "provider": "scaleway",
    "model": "llama-3.3-70B",
    "prompt": "Écris un résumé clair et concis de cet amendement en utilisant l'exposé suivant : {{expose}}",
    }
  }
}
```

**Response:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Objet amdt": "Generated summary of the amendment",
      // Other amendment fields
    }
    // More amendments
  ]
}
```

**Configuration Parameters:**

| Parameter           | Type    | Required | Description                                                     |
| ------------------- | ------- | -------- | --------------------------------------------------------------- |
| summary_column      | string  | No       | Column to store the generated summaries (default: "Objet amdt") |
| should_overwrite    | boolean | No       | Whether to overwrite existing summaries (default: true)         |
| llm_config          | object  | No       | Configuration for the language model                            |
| llm_config.provider | string  | No       | LLM provider (e.g., "scaleway")                                 |
| llm_config.model    | string  | No       | Model to use (e.g., "llama-3.3-70B")                            |
| llm_config.prompt   | string  | No       | Prompt template for summary generation                          |

### 3. Past Similarity Search Endpoint

**Endpoint:** `/api/similarity/past`

**Method:** POST

**Description:** Finds similar amendments from a database of past amendments.

**Request Body:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "columns_to_copy": {
      "Réponse": {
        "enabled": true
      },
      "Sort": {
        "enabled": true,
        "condition": "irrecevable"
      },
      "Objet amdt": {
        "enabled": false
      }
    },
    "clustering_similarity_thresholds": {
      "Exposé amdt": 0.4,
      "Corps amdt": 0.4
    },
    "fuzzy_match_similarity_thresholds": {
      "Exposé amdt": 0.4,
      "Corps amdt": 0.9
    },
    "similarity_threshold_overrides": {
      "Exposé amdt": {
        "amendement redactionnel": 0.95
      }
    },
    "column_group_by_columns": {
      "Corps amdt": ["Num article"]
    }
  }
}
```

**Response:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Réponse": "Response copied from similar past amendment",
      "Sort": "Sort copied from similar past amendment",
      // Other amendment fields
    }
    // More amendments
  ]
}
```

**Configuration Parameters:**

| Parameter                               | Type    | Required | Description                                                     |
| --------------------------------------- | ------- | -------- | --------------------------------------------------------------- |
| columns_to_copy                         | object  | Yes      | Configuration for which columns to copy from similar amendments |
| columns_to_copy.[column_name].enabled   | boolean | Yes      | Whether to copy this column                                     |
| columns_to_copy.[column_name].condition | string  | No       | Only copy if this condition matches                             |
| clustering_similarity_thresholds        | object  | No       | Thresholds for clustering by column                             |
| fuzzy_match_similarity_thresholds       | object  | No       | Thresholds for fuzzy matching by column within a cluster        |
| similarity_threshold_overrides          | object  | No       | Override thresholds for specific text patterns                  |
| column_group_by_columns                 | object  | No       | Columns to group by before comparing, by column                 |

### 4. Within-Lecture Similarity Search Endpoint

**Endpoint:** `/api/similarity/within`

**Method:** POST

**Description:** Finds similarities between amendments within the same set.

**Request Body:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "column": "Exposé amdt",
    "similarity_threshold": 0.8,
    "group_by_columns": ["Num article"],
    "clustering_similarity_thresholds": 0.4
  }
}
```

**Response:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Commentaires": "Similar to amendments: 124, 125",
      // Other amendment fields
    }
    // More amendments
  ],
  "similarity_results": {
    "1": [
      {
        "Num amdt": "124",
        "similarity_score": 0.92
      },
      {
        "Num amdt": "125",
        "similarity_score": 0.85
      }
    ]
    // More similarity results
  }
}
```

**Configuration Parameters:**

| Parameter                        | Type   | Required | Description                                                       |
| -------------------------------- | ------ | -------- | ----------------------------------------------------------------- |
| column                           | string | Yes      | Column used for similarity comparison (e.g., "Exposé amdt")       |
| similarity_threshold             | float  | Yes      | Threshold above which amendments are considered similar (0.0-1.0) |
| group_by_columns                 | array  | No       | Columns to group by before comparing (e.g., ["Num article"])      |
| clustering_similarity_thresholds | float  | No       | TF-IDF threshold for clustering (default: 0.4)                    |

### 5. Attribution Endpoint

**Endpoint:** `/api/attribution`

**Method:** POST

**Description:** Assigns amendments to appropriate entities based on content analysis.

**Request Body:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "project_name": "PLF",
    "interstitial_only": false,
    "directory": {
      "type": "s3",
      "path": "s3://bucket-name/path/to/amendments.json",
      "format": "json"
    },
  }
}
```

**Response:**

```json
{
  "amendments": [
    {
      "amdt_idx": 1,
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Affectation (email)": "user@example.com",
      "Affectation (nom)": "User Name",
      "Entité Pilote": "Entity Name",
      // Other amendment fields
    }
    // More amendments
  ]
}
```

**Configuration Parameters:**

| Parameter         | Type    | Required | Description                                                                                           |
| ----------------- | ------- | -------- | ----------------------------------------------------------------------------------------------------- |
| project_name      | string  | Yes      | Name of the project for attribution rules (e.g., "PLF")                                               |
| interstitial_only | boolean | No       | Whether to only process amendments with article numbers starting with "article add." (default: false) |
| directory            | object | No       | Configuration for directory containing attribution rules                         |
| directory.type       | string | No       | Type of storage for directory ("s3", "local", etc.)                            |
| directory.path       | string | No       | Path to the directory file                                                      |
| directory.format     | string | No       | Format of the directory file ("json", "excel", etc.)                           |

### 6. Add New Amendments Endpoint

**Endpoint:** `/api/amendments/add`

**Method:** POST

**Description:** Adds new amendments to the database for future similarity searches.

**Request Body (JSON data):**

```json
{
  "amendments": [
    {
      "Num amdt": "123",
      "Corps amdt": "Text of the amendment body",
      "Exposé amdt": "Explanation of the amendment",
      "Num article": "Article 1",
      "Réponse": "Government response",
      "Sort": "Status of the amendment",
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "origin_project": "PLF 2025",
    "processing_timestamp": {
      "year": 2025,
      "month": 4,
      "day": 28
    },
    "drop_empty_columns": ["Réponse"]
  }
}
```

**Request Body (File Upload):**

```json
{
  "file_source": {
    "type": "s3",
    "path": "s3://bucket-name/path/to/amendments.json",
    "format": "json"
  },
  "config": {
    "origin_project": "PLF 2025",
    "processing_timestamp": {
      "year": 2025,
      "month": 4,
      "day": 28
    },
    "drop_empty_columns": ["Réponse"]
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Successfully added 100 amendments to the database",
  "amendments_added": 100,
  "amendments_skipped": 5,
  "database_size": 1050
}
```

**Configuration Parameters:**

| Parameter                  | Type    | Required | Description                                            |
| -------------------------- | ------- | -------- | ------------------------------------------------------ |
| origin_project             | string  | Yes      | Name of the project the amendments belong to           |
| processing_timestamp       | object  | Yes      | Timestamp for when the amendments were processed       |
| processing_timestamp.year  | integer | Yes      | Year                                                   |
| processing_timestamp.month | integer | Yes      | Month                                                  |
| processing_timestamp.day   | integer | Yes      | Day                                                    |
| drop_empty_columns         | array   | No       | Columns to drop rows from if they are empty            |
| file_source                | object  | No       | Configuration for file source (for file upload method) |
| file_source.type           | string  | No       | Type of file source ("s3", "local", etc.)              |
| file_source.path           | string  | No       | Path to the file                                       |
| file_source.format         | string  | No       | Format of the file ("json", "excel", etc.)             |
