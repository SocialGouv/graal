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
      "Mission": "mission title"
      // Other amendment fields
    }
    // More amendments
  ],
  "config": {
    "column": "Corps amdt",
    "similarity_threshold": 0.999,
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
| directory         | object  | No       | Configuration for directory containing attribution rules                                              |
| directory.type    | string  | No       | Type of storage for directory ("s3", "local", etc.)                                                   |
| directory.path    | string  | No       | Path to the directory file                                                                            |
| directory.format  | string  | No       | Format of the directory file ("json", "excel", etc.)                                                  |

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

## Database Builder Endpoints

### 7. Upload File to Pool

**Endpoint:** `/databases/upload-file`

**Method:** POST

**Description:** Uploads a file to the shared pool with hash-based deduplication. Files are stored in S3 with their content hash as the filename, ensuring identical files are only stored once. Returns metadata including whether the file already existed in the pool.

**Request Body:**

Form-data with file upload:
- `file`: The file to upload (multipart/form-data)

**Response:**

```json
{
  "upload_id": "unique-id",
  "filename": "lecture-2024-01.json",
  "file_hash": "<abc123def456>",
  "s3_key": "input_files/pool/abc123def456.json",
  "already_existed": false
}
```

**Response Fields:**

| Field           | Type    | Description                                                   |
| --------------- | ------- | ------------------------------------------------------------- |
| upload_id       | string  | Unique identifier for this upload reference                   |
| filename        | string  | Original filename provided by user                            |
| file_hash       | string  | SHA-256 hash of the file content                              |
| s3_key          | string  | S3 key where the file is stored in the pool                   |
| already_existed | boolean | Whether this file already existed in the pool (deduplication) |

### 8. Build Database

**Endpoint:** `/databases/build`

**Method:** POST

**Description:** Builds a new similarity database from uploaded files. Creates a manifest tracking all files included in the database. Files remain in the S3 pool for reuse in other databases or appending operations.

**Request Body:**

```json
{
  "database_name": "PLFSS_2024",
  "file_references": [
    {
      "upload_id": "unique-id-1",
      "filename": "lecture-2024-01.json",
      "file_hash": "<abc123def456>",
      "metadata": {
        "default_processing_timestamp": 1704067200,
        "origin_project": "PLFSS 2024"
      }
    },
    {
      "upload_id": "unique-id-2",
      "filename": "lecture-2024-02.json",
      "file_hash": "<def789ghi012>",
      "metadata": {
        "default_processing_timestamp": 1704153600,
        "origin_project": "PLFSS 2024"
      }
    }
  ],
  "drop_empty_columns": ["Réponse"],
  "similarity_threshold": 0.99,
  "eps": 0.4,
  "group_by_columns": ["Lecture", "origin_project", "Num article"]
}
```

**Response:**

```json
{
  "status": "processing",
  "job_id": "job-abc123",
  "message": "Database build started"
}
```

**Configuration Parameters:**

| Parameter                   | Type   | Required | Description                                         |
| --------------------------- | ------ | -------- | --------------------------------------------------- |
| database_name               | string | Yes      | Name of the database to create                      |
| file_references             | array  | Yes      | Array of file references to include in the database |
| file_references[].upload_id | string | Yes      | Upload ID from the upload-file endpoint             |
| file_references[].filename  | string | Yes      | Original filename                                   |
| file_references[].file_hash | string | Yes      | File hash from the upload-file endpoint             |
| file_references[].metadata  | object | Yes      | Metadata for the file                               |
| drop_empty_columns          | array  | No       | Columns to drop if they are empty                   |
| similarity_threshold        | float  | No       | Threshold for similarity detection (default: 0.99)  |
| eps                         | float  | No       | DBSCAN clustering epsilon parameter (default: 0.4)  |
| group_by_columns            | array  | No       | Columns to group by before similarity detection     |

**Note:** Files remain in the S3 pool after building the database, allowing them to be reused in other databases or for appending operations.

### 9. Append Files to Database

**Endpoint:** `/databases/by-id/{db_id}/append`

**Method:** POST

**Description:** Appends additional files to an existing database and rebuilds it with all files (original + new). The database manifest is updated to track all included files.

**Path Parameters:**

| Parameter | Type | Required | Description                            |
| --------- | ---- | -------- | -------------------------------------- |
| db_id     | uuid | Yes      | Manifest UUID of the existing database |

**Request Body:**

```json
{
  "file_references": [
    {
      "upload_id": "unique-id-3",
      "filename": "lecture-2024-03.json",
      "file_hash": "ghi345jkl678",
      "metadata": {
        "default_processing_timestamp": 1704240000,
        "origin_project": "PLFSS 2024"
      }
    }
  ],
  "drop_empty_columns": ["Réponse"],
  "similarity_threshold": 0.99,
  "eps": 0.4,
  "group_by_columns": ["Lecture", "origin_project", "Num article"]
}
```

**Response:**

```json
{
  "status": "processing",
  "job_id": "job-def456",
  "message": "Database append started"
}
```

**Configuration Parameters:**

| Parameter                   | Type   | Required | Description                                            |
| --------------------------- | ------ | -------- | ------------------------------------------------------ |
| file_references             | array  | Yes      | Array of new file references to append to the database |
| file_references[].upload_id | string | Yes      | Upload ID from the upload-file endpoint                |
| file_references[].filename  | string | Yes      | Original filename                                      |
| file_references[].file_hash | string | Yes      | File hash from the upload-file endpoint                |
| file_references[].metadata  | object | Yes      | Metadata for the file                                  |
| drop_empty_columns          | array  | No       | Columns to drop if they are empty                      |
| similarity_threshold        | float  | No       | Threshold for similarity detection (default: 0.99)     |
| eps                         | float  | No       | DBSCAN clustering epsilon parameter (default: 0.4)     |
| group_by_columns            | array  | No       | Columns to group by before similarity detection        |

**Process:**
1. Loads the existing database manifest
2. Adds new file references to the manifest
3. Rebuilds the database from ALL files (original + new) in the S3 pool
4. Uploads the new Parquet database file
5. Saves the updated manifest

### 10. Get Database Manifest

**Endpoint:** `/databases/by-id/{db_id}/manifest`

**Method:** GET

**Description:** Retrieves the manifest for a database, showing all files included in it along with their metadata.

**Path Parameters:**

| Parameter | Type | Required | Description                   |
| --------- | ---- | -------- | ----------------------------- |
| db_id     | uuid | Yes      | Manifest UUID of the database |

**Response:**

```json
{
  "database_name": "PLFSS_2024",
  "created_at": "2024-01-15T10:30:00Z",
  "last_updated_at": "2024-02-20T15:45:00Z",
  "files": [
    {
      "upload_id": "unique-id-1",
      "filename": "lecture-2024-01.json",
      "file_hash": "<abc123def456>",
      "uploaded_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "default_processing_timestamp": 1704067200,
        "origin_project": "PLFSS 2024"
      }
    },
    {
      "upload_id": "unique-id-2",
      "filename": "lecture-2024-02.json",
      "file_hash": "<def789ghi012>",
      "uploaded_at": "2024-01-15T11:00:00Z",
      "metadata": {
        "default_processing_timestamp": 1704153600,
        "origin_project": "PLFSS 2024"
      }
    }
  ],
  "total_files": 2
}
```

**Response Fields:**

| Field               | Type    | Description                                              |
| ------------------- | ------- | -------------------------------------------------------- |
| database_name       | string  | Name of the database                                     |
| created_at          | string  | ISO 8601 timestamp when the database was first created   |
| last_updated_at     | string  | ISO 8601 timestamp when the database was last updated    |
| files               | array   | Array of file references included in the database        |
| files[].upload_id   | string  | Upload ID of the file                                    |
| files[].filename    | string  | Original filename                                        |
| files[].file_hash   | string  | SHA-256 hash of the file content                         |
| files[].uploaded_at | string  | ISO 8601 timestamp when the file was uploaded            |
| files[].metadata    | object  | File metadata including processing timestamp and project |
| total_files         | integer | Total number of files in the database                    |
