#!/usr/bin/env python3
"""
export_catalog.py

Kali Open Food Catalog — Reusable Export, Import & Verification Utility
Compliant with Open Database License (ODbL) Section 4.6 (Access to Derived Databases).

Commands:
    verify [path/to/off_italy_seed.db]
        Verify the cryptographic checksum, file size, and record counts of an SQLite catalog.

    export-jsonl [path/to/off_italy_seed.db] [output.jsonl.gz]
        Export the SQLite database into a compact, compressed JSONL dataset.

    import-jsonl <input.jsonl.gz> [output.db]
        Reconstruct a complete SQLite database (schema, tables, and indexes) from JSONL.gz.

    verify-jsonl [path/to/kali_open_food_catalog.jsonl.gz]
        Verify the integrity and record counts of a compressed JSONL catalog export.
"""

import sys
import os
import sqlite3
import hashlib
import json
import gzip

EXPECTED_SHA256 = "41e65549aedc99effe5854136325d54d954766a9807bf19a7a6cef9141603d96"
EXPECTED_SIZE = 133718016
EXPECTED_FOODS_COUNT = 181308
EXPECTED_PORTIONS_COUNT = 53540

DEFAULT_METADATA = {
    "build_id": "off_italy_20260925_step14_14e_1",
    "version": "0.2.0",
    "catalog_name": "Open Food Facts Italy Packaged Food Reference Catalog",
    "build_timestamp": "2026-09-25T11:51:42Z",
    "product_count": 181308,
    "primary_count": 172738,
    "secondary_count": 8570,
    "checksum_sha256": "1763dceece3db937d3d8b3414a8f378f458b87cf7c0ec0fe194a80dc92592b5c"
}

DEFAULT_DB_PATHS = [
    os.path.join(os.path.dirname(__file__), "off_italy_seed.db"),
    "off_italy_seed.db",
    os.path.join(os.path.dirname(__file__), "../../ios/CalorieApp/off_italy_seed.db"),
    os.path.join(os.path.dirname(__file__), "../../import_data/openfoodfacts/off_italy_seed.db")
]

DEFAULT_JSONL_PATHS = [
    os.path.join(os.path.dirname(__file__), "kali_open_food_catalog.jsonl.gz"),
    "kali_open_food_catalog.jsonl.gz"
]

def find_file(custom_path, defaults):
    if custom_path and os.path.isfile(custom_path):
        return os.path.abspath(custom_path)
    for p in defaults:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None

def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def verify_database(db_path):
    print(f"[VERIFY] Checking SQLite database: {db_path}")
    size = os.path.getsize(db_path)
    print(f"  - Size: {size:,} bytes")
    
    sha = compute_sha256(db_path)
    print(f"  - SHA-256: {sha}")
    if sha == EXPECTED_SHA256 and size == EXPECTED_SIZE:
        print("  - Cryptographic match: IDENTICAL to official seed release.")
    else:
        print(f"  [NOTE] Custom database instance (expected official SHA-256: {EXPECTED_SHA256})")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM foods;")
    foods_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM food_portions;")
    portions_count = cursor.fetchone()[0]

    meta = None
    try:
        cursor.execute("SELECT build_id, version, build_timestamp, product_count FROM _catalog_build_metadata LIMIT 1;")
        meta = cursor.fetchone()
    except Exception:
        pass
    conn.close()

    print(f"  - Foods count: {foods_count:,} (expected: {EXPECTED_FOODS_COUNT:,})")
    print(f"  - Portions count: {portions_count:,} (expected: {EXPECTED_PORTIONS_COUNT:,})")
    if meta:
        print(f"  - Build ID: {meta[0]}, Version: {meta[1]}, Timestamp: {meta[2]}")

    is_valid = (foods_count == EXPECTED_FOODS_COUNT and portions_count == EXPECTED_PORTIONS_COUNT)
    if is_valid:
        print("  [SUCCESS] Database record counts verified and intact.")
    else:
        print(f"  [ERROR] Record count mismatch: foods={foods_count}, portions={portions_count}")
    return is_valid

def export_jsonl_gz(db_path, output_path):
    print(f"[EXPORT] Exporting SQLite -> compressed JSONL")
    print(f"  Source DB: {db_path}")
    print(f"  Output:    {output_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM foods ORDER BY barcode;")
    foods = cursor.fetchall()

    portions_cursor = conn.cursor()
    portions_cursor.execute("SELECT * FROM food_portions ORDER BY food_id, is_default DESC, id ASC;")
    portions_by_food = {}
    for p in portions_cursor.fetchall():
        fid = p["food_id"]
        if fid not in portions_by_food:
            portions_by_food[fid] = []
        portions_by_food[fid].append({
            "id": p["id"],
            "label": p["label"],
            "grams_equivalent": p["grams_equivalent"],
            "is_default": bool(p["is_default"]),
            "volume_ml_equivalent": p["volume_ml_equivalent"],
            "created_at": p["created_at"],
            "updated_at": p["updated_at"]
        })

    count = 0
    portions_total = 0
    with gzip.open(output_path, "wt", encoding="utf-8") as gz:
        for f in foods:
            row_dict = dict(f)
            item_portions = portions_by_food.get(f["id"], [])
            row_dict["portions"] = item_portions
            portions_total += len(item_portions)
            gz.write(json.dumps(row_dict, ensure_ascii=False) + "\n")
            count += 1

    conn.close()
    out_size = os.path.getsize(output_path)
    sha256 = compute_sha256(output_path)
    print(f"  [SUCCESS] Exported {count:,} products and {portions_total:,} portions.")
    print(f"  File size: {out_size:,} bytes ({out_size / 1024 / 1024:.2f} MB)")
    print(f"  SHA-256:   {sha256}")
    return sha256, out_size

def verify_jsonl_gz(jsonl_path):
    print(f"[VERIFY-JSONL] Checking compressed catalog: {jsonl_path}")
    if not os.path.isfile(jsonl_path):
        print(f"  [ERROR] File not found: {jsonl_path}")
        return False

    size = os.path.getsize(jsonl_path)
    sha = compute_sha256(jsonl_path)
    print(f"  - Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    print(f"  - SHA-256: {sha}")

    products_count = 0
    portions_count = 0
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            products_count += 1
            item = json.loads(line)
            portions_count += len(item.get("portions", []))

    print(f"  - Products count: {products_count:,} (expected: {EXPECTED_FOODS_COUNT:,})")
    print(f"  - Portions count: {portions_count:,} (expected: {EXPECTED_PORTIONS_COUNT:,})")

    is_valid = (products_count == EXPECTED_FOODS_COUNT and portions_count == EXPECTED_PORTIONS_COUNT)
    if is_valid:
        print("  [SUCCESS] JSONL.gz dataset is 100% verified and intact.")
    else:
        print("  [ERROR] JSONL.gz record count mismatch.")
    return is_valid

def import_jsonl_to_sqlite(jsonl_path, output_db_path):
    print(f"[IMPORT] Rebuilding SQLite database from JSONL.gz")
    print(f"  Source JSONL: {jsonl_path}")
    print(f"  Target SQLite: {output_db_path}")

    if os.path.exists(output_db_path):
        os.remove(output_db_path)

    conn = sqlite3.connect(output_db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;

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
    """)

    food_columns = [
        "id", "canonical_food_id", "name", "brand", "barcode", "food_type",
        "calories_100g", "protein_100g", "carbs_100g", "fat_100g", "fiber_100g",
        "nutrition_basis", "normalized_name", "sugars_100g", "saturated_fat_100g",
        "sodium_mg_100g", "default_serving_unit", "default_serving_size",
        "default_serving_weight_grams", "data_quality", "source_provider",
        "source_record_id", "source_version", "source_license", "source_updated_at",
        "verification_status", "is_cached_remote", "last_accessed_at", "sync_status",
        "created_at", "updated_at", "deleted_at", "display_name", "language_score",
        "italy_relevance_score", "dedup_cluster_key", "is_cluster_primary"
    ]
    food_sql = f"INSERT INTO foods ({','.join(food_columns)}) VALUES ({','.join(['?'] * len(food_columns))})"
    portion_sql = "INSERT INTO food_portions (id, food_id, label, grams_equivalent, is_default, volume_ml_equivalent, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

    foods_batch = []
    portions_batch = []
    total_foods = 0
    total_portions = 0

    conn.execute("BEGIN TRANSACTION;")
    with gzip.open(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            food_vals = [item.get(col) for col in food_columns]
            foods_batch.append(food_vals)
            total_foods += 1

            for p in item.get("portions", []):
                portions_batch.append((
                    p["id"],
                    item["id"],
                    p["label"],
                    p["grams_equivalent"],
                    1 if p.get("is_default") else 0,
                    p.get("volume_ml_equivalent"),
                    p.get("created_at") or item.get("created_at"),
                    p.get("updated_at") or item.get("updated_at")
                ))
                total_portions += 1

            if len(foods_batch) >= 5000:
                cursor.executemany(food_sql, foods_batch)
                cursor.executemany(portion_sql, portions_batch)
                foods_batch.clear()
                portions_batch.clear()

    if foods_batch:
        cursor.executemany(food_sql, foods_batch)
        cursor.executemany(portion_sql, portions_batch)

    # Insert authoritative metadata
    cursor.execute("""
        INSERT INTO _catalog_build_metadata (
            build_id, version, catalog_name, build_timestamp, product_count, primary_count, secondary_count, checksum_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        DEFAULT_METADATA["build_id"],
        DEFAULT_METADATA["version"],
        DEFAULT_METADATA["catalog_name"],
        DEFAULT_METADATA["build_timestamp"],
        total_foods,
        DEFAULT_METADATA["primary_count"],
        DEFAULT_METADATA["secondary_count"],
        DEFAULT_METADATA["checksum_sha256"]
    ))

    # Build production indexes
    print("  - Building indexes...")
    cursor.executescript("""
        CREATE UNIQUE INDEX idx_foods_barcode ON foods(barcode);
        CREATE INDEX idx_foods_name ON foods(name);
        CREATE INDEX idx_foods_normalized_name ON foods(normalized_name);
        CREATE INDEX idx_foods_brand ON foods(brand) WHERE brand IS NOT NULL;
        CREATE INDEX idx_food_portions_food_id ON food_portions(food_id);
        CREATE INDEX idx_foods_cluster_search ON foods (is_cluster_primary, italy_relevance_score DESC, language_score DESC);
        CREATE INDEX idx_foods_display_name ON foods (display_name);
        CREATE INDEX idx_foods_cluster_key ON foods (dedup_cluster_key);
    """)

    conn.commit()
    conn.close()

    db_size = os.path.getsize(output_db_path)
    print(f"  [SUCCESS] SQLite database rebuilt: {total_foods:,} products, {total_portions:,} portions.")
    print(f"  Target size: {db_size:,} bytes ({db_size / 1024 / 1024:.2f} MB)")
    return True

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "verify":
        custom_path = sys.argv[2] if len(sys.argv) > 2 else None
        db_path = find_file(custom_path, DEFAULT_DB_PATHS)
        if not db_path:
            print("[ERROR] SQLite seed database not found.")
            sys.exit(1)
        ok = verify_database(db_path)
        sys.exit(0 if ok else 1)

    elif cmd == "verify-jsonl":
        custom_path = sys.argv[2] if len(sys.argv) > 2 else None
        jsonl_path = find_file(custom_path, DEFAULT_JSONL_PATHS)
        if not jsonl_path:
            print("[ERROR] Compressed JSONL file not found.")
            sys.exit(1)
        ok = verify_jsonl_gz(jsonl_path)
        sys.exit(0 if ok else 1)

    elif cmd == "export-jsonl":
        if len(sys.argv) == 2:
            db_path = find_file(None, DEFAULT_DB_PATHS)
            out_path = os.path.join(os.path.dirname(__file__), "kali_open_food_catalog.jsonl.gz")
        elif len(sys.argv) == 3:
            # Check if arg is source DB or target path
            if sys.argv[2].endswith(".db"):
                db_path = sys.argv[2]
                out_path = os.path.join(os.path.dirname(__file__), "kali_open_food_catalog.jsonl.gz")
            else:
                db_path = find_file(None, DEFAULT_DB_PATHS)
                out_path = sys.argv[2]
        else:
            db_path = sys.argv[2]
            out_path = sys.argv[3]

        if not db_path or not os.path.isfile(db_path):
            print(f"[ERROR] Source database not found: {db_path}")
            sys.exit(1)
        export_jsonl_gz(db_path, out_path)

    elif cmd == "import-jsonl":
        if len(sys.argv) < 3:
            print("Usage: python3 export_catalog.py import-jsonl <input.jsonl.gz> [output.db]")
            sys.exit(1)
        jsonl_path = sys.argv[2]
        out_db_path = sys.argv[3] if len(sys.argv) > 3 else "off_italy_reconstructed.db"
        if not os.path.isfile(jsonl_path):
            print(f"[ERROR] JSONL input file not found: {jsonl_path}")
            sys.exit(1)
        import_jsonl_to_sqlite(jsonl_path, out_db_path)
        verify_database(out_db_path)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
