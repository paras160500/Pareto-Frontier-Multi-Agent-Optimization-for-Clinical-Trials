"""
    MIMIC-III loader.

    Acces the MIMIC-III credentials before running this, we must have 
    1. Get access at https://phycionet.org/content/mimiciii/1.4
    2. Download pateients.csv , diagnoses_ics.scv, labevents.csv
    3. Place them inside ./data/mimic_db/mimiciii_csvs/
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import os 
import duckdb
from data_pipeline.paths import data_paths

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                     Function Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def load_real_mimic_data():
    """
        Loads real MIMIC-III csv intor DuckDB database. Returns db_path or None if files were missing.
    """
    print("Attempting to load readl MIMIC-III data from local csv")
    db_path = os.path.join(data_paths['mimic'] , "mimic3_real.db")
    csv_dir = os.path.join(data_paths['mimic'] , "mimiciii_csvs")

    required_files = {
        "patients" : os.path.join(csv_dir , "PATIENTS.csv"),
        "diagnoses" : os.path.join(csv_dir , "DIAGNOSES_ICD.csv"),
        "labevents" : os.path.join(csv_dir , "LABEVENTS.csv")
    }

    missing_files = [path for path in required_files.values() if not os.path.exists(path)]
    if missing_files:
        print(f"ERROR : The following MIMIC-III files were not found:")
        for f in missing_files:
            print(f"- {f}")
        print("\nPlease download them as instructured and place them in the correct directory")
        return None 

    print("Required files found")
    if os.path.exists(db_path):
        os.remove(db_path)
    con = duckdb.connect(db_path)

    print(f"Loading {required_files['patients']} into DuckDB...")
    con.execute(
        f"CREATE TABLE patients AS SELECT SUBJECT_ID, GENDER, DOB, DOD FROM read_csv_auto('{required_files['patients']}')"
    )

    print(f"Loading {required_files['diagnoses']} into DuckDB...")
    con.execute(
        f"CREATE TABLE diagnoses_icd AS SELECT SUBJECT_ID, ICD9_CODE FROM read_csv_auto('{required_files['diagnoses']}')"
    )

    print(f"Loading and processing {required_files['labevents']} (this may take several minutes)...")
    # Labevents is huge. Read as all text to avoid type errors, filter to our specific
    # numeric lab items, then convert.
    con.execute(
        f"""CREATE TABLE labevents_staging AS
               SELECT SUBJECT_ID, ITEMID, VALUENUM
               FROM read_csv_auto('{required_files['labevents']}', all_varchar=True)
               WHERE ITEMID IN ('50912', '50852') AND VALUENUM IS NOT NULL AND VALUENUM ~ '^[0-9]+(\\.[0-9]+)?$'
            """
    )
    con.execute(
        "CREATE TABLE labevents AS SELECT SUBJECT_ID, CAST(ITEMID AS INTEGER) AS ITEMID, "
        "CAST(VALUENUM AS DOUBLE) AS VALUENUM FROM labevents_staging"
    )
    con.execute("DROP TABLE labevents_staging")

    con.close()
    return db_path


def preview_mimic_db(db_path: str) -> None:
    """Prints table list and sample rows, same sanity check as the notebook."""
    print("\nTesting database connection and schema...")
    con = duckdb.connect(db_path)
    print(f"Tables in DB: {con.execute('SHOW TABLES').df()['name'].tolist()}")
    print("\nSample of 'patients' table:")
    print(con.execute("SELECT * FROM patients LIMIT 5").df())
    print("\nSample of 'diagnoses_icd' table:")
    print(con.execute("SELECT * FROM diagnoses_icd LIMIT 5").df())
    con.close()