# Kali Open Food Catalog (Italian Packaged Foods Dataset)

## Overview & Attribution

This dataset contains **181,308 packaged food products** and **53,540 portion measurements** sold on the Italian market, derived from **Open Food Facts** (https://world.openfoodfacts.org).

This dataset is made available under the terms of the **Open Database License (ODbL) v1.0**:
https://opendatacommons.org/licenses/odbl/1-0/

Any individual contents of the database are licensed under the **Database Contents License (DbCL) v1.0**:
https://opendatacommons.org/licenses/dbcl/1-0/

> **Attribution Notice**:
> Contains information from Open Food Facts, which is made available under the Open Database License (ODbL) v1.0.
> Open Food Facts is not the author, sponsor, or official endorser of Kali. All trademarks and brand names belong to their respective owners.

---

## Technical Measures for ODbL Section 4.6 Alignment (Access to Derived Databases)

Under Section 4.6 of the Open Database License (ODbL) v1.0, recipients of a Produced Work or Derived Database are entitled to access the Derived Database in a machine-readable format. From an engineering and open data perspective, this package provides:
1. **Machine-Readable Metadata**: Complete specifications, schema DDL, and column definitions (`metadata.json`).
2. **Deterministic Checksum Verification**: Cryptographic SHA-256 verification utility (`export_catalog.py verify` and `export_catalog.py verify-jsonl`).
3. **Reproducible Transformation Specifications**: Documentation of filtering, deduplication clustering, and normalization criteria.
4. **Independent Export & Rebuild Tools**: Standard SQLite database schema and compressed JSONL representations with a bidirectional import utility (`export_catalog.py import-jsonl`).

*Notice on Legal Assessment*: These technical artifacts are designed to facilitate compliance with open data sharing principles under ODbL Section 4.6. However, technical availability does not constitute a formal legal opinion or legal advice. Independent legal evaluation should be sought regarding statutory compliance across specific jurisdictions.

---

## Dataset Characteristics & Verification

- **Build ID**: `off_italy_20260925_step14_14e_1`
- **Release Version**: `0.2.0`
- **Dataset Date**: September 24–25, 2026
- **Primary Source Provider**: Open Food Facts (`open_food_facts`)
- **Market Scope**: Italy (products with valid barcodes sold in domestic retail chains or labeled in Italian)
- **File Name**: `off_italy_seed.db`
- **File Size**: `133,718,016` bytes (127.52 MB)
- **SHA-256 Checksum**:  
  `41e65549aedc99effe5854136325d54d954766a9807bf19a7a6cef9141603d96`
- **Unique Barcodes**: 181,308 (100% addressable)
- **Portion Measurements**: 53,540 verified servings

---

## Applied Transformations & Normalizations

This Derived Database was prepared through systematic filtering and normalization scripts:
1. **Market Filtering & Scope**:
   - Filtered for products sold in Italy, distributed in Italian retail chains (e.g. Esselunga, Conad, Coop, Eurospin, Carrefour, Pam), or having Italian product titles.
   - Strictly requires valid EAN/UPC barcodes (`length >= 4`, leading zeros preserved as strings).
2. **Nutrition Basis Separation & Quality Quarantine**:
   - Explicit mass units mapped to `per_100g`.
   - Explicit volume units mapped to `per_100ml`.
   - Products with ambiguous basis or missing core macronutrients were quarantined and excluded to ensure nutritional integrity.
3. **Display Name Normalization**:
   - Cleaned redundant packaging symbols (®, ™, ©, emoji).
   - Stripped duplicate brand name repetition in product titles.
   - Cleaned broken whitespace and punctuation while strictly preserving all semantic nouns and original product descriptions (zero automated translations).
4. **Italian Relevance & Language Scoring**:
   - Computed `language_score` and `italy_relevance_score` based on Italian brand signals and store keywords to optimize search relevance ranking.
5. **Deduplication Clustering**:
   - Grouped duplicate product entries into clusters (`dedup_cluster_key`).
   - The primary entry is marked with `is_cluster_primary = 1` (172,738 primaries).
   - 100% of physical barcodes remain stored and queryable.

---

## Photographic Content & Privacy Audit

- **No Images or URLs**: The database contains **zero image files, zero binary blobs, and zero image URL columns**.
- **License Boundary**: The Creative Commons CC-BY-SA license applicable to photographs on Open Food Facts does **not** apply to this dataset, as no photos or photo URLs are distributed.
- **Zero Personal Data**: The dataset contains exclusively public food nutritional information. Zero user profile data, credentials, device identifiers, or contributor identities are included.

---

## Database Schema (DDL)

```sql
CREATE TABLE foods (
    id TEXT PRIMARY KEY,
    canonical_food_id TEXT,
    name TEXT NOT NULL,
    brand TEXT,
    barcode TEXT UNIQUE,
    food_type TEXT NOT NULL DEFAULT 'branded',
    calories_100g REAL NOT NULL,
    protein_100g REAL NOT NULL,
    carbs_100g REAL NOT NULL,
    fat_100g REAL NOT NULL,
    fiber_100g REAL,
    nutrition_basis TEXT NOT NULL DEFAULT 'per_100g',
    normalized_name TEXT,
    sugars_100g REAL,
    saturated_fat_100g REAL,
    sodium_mg_100g REAL,
    default_serving_unit TEXT,
    default_serving_size REAL,
    default_serving_weight_grams REAL,
    data_quality TEXT NOT NULL DEFAULT 'high',
    source_provider TEXT NOT NULL DEFAULT 'open_food_facts',
    source_record_id TEXT,
    source_version TEXT DEFAULT '2026-09-24',
    source_license TEXT DEFAULT 'ODbL-1.0',
    source_updated_at TEXT,
    verification_status TEXT NOT NULL DEFAULT 'community_submitted',
    is_cached_remote INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT,
    sync_status TEXT NOT NULL DEFAULT 'local_only',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    display_name TEXT,
    language_score INTEGER DEFAULT 1,
    italy_relevance_score INTEGER DEFAULT 2,
    dedup_cluster_key TEXT,
    is_cluster_primary INTEGER DEFAULT 1
);

CREATE TABLE food_portions (
    id TEXT PRIMARY KEY,
    food_id TEXT NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    grams_equivalent REAL NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    volume_ml_equivalent REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE _catalog_build_metadata (
    build_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    catalog_name TEXT NOT NULL,
    build_timestamp TEXT NOT NULL,
    product_count INTEGER NOT NULL,
    primary_count INTEGER NOT NULL,
    secondary_count INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL
);
```

---

## File Checksums & Sizes

| Artifact | File Name | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|
| **Compressed Catalog** | `kali_open_food_catalog.jsonl.gz` | `15,482,284` (14.77 MB) | `7842cfe1062da222cb99629bdbab34833f682572acef7a72cbab3f30ff806e90` |
| **SQLite Seed Catalog** | `off_italy_seed.db` | `133,718,016` (127.52 MB) | `41e65549aedc99effe5854136325d54d954766a9807bf19a7a6cef9141603d96` |

---

## Usage & Verification

### 1. Verify Compressed Dataset
To verify the integrity and exact record counts of the compressed JSONL file:
```bash
python3 export_catalog.py verify-jsonl kali_open_food_catalog.jsonl.gz
```

### 2. Reconstruct SQLite Database from JSONL.gz
To rebuild the complete, indexed SQLite database from the compressed dataset:
```bash
python3 export_catalog.py import-jsonl kali_open_food_catalog.jsonl.gz off_italy_seed.db
```

### 3. Verify SQLite Database
To verify record counts, schema tables, and metadata of an SQLite database:
```bash
python3 export_catalog.py verify off_italy_seed.db
```

### 4. Re-export SQLite to Compressed JSONL
To re-export an SQLite database into compressed JSONL format:
```bash
python3 export_catalog.py export-jsonl off_italy_seed.db kali_open_food_catalog.jsonl.gz
```

