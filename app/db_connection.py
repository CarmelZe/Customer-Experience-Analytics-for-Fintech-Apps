import oracledb
import pandas as pd
from datetime import datetime

class OracleDBManager:
    def __init__(self, username, password, dsn="localhost/XE"):
        self.username = username
        self.password = password
        self.dsn = dsn
        self.connection = None

    def connect(self):
        try:
            self.connection = oracledb.connect(
                user=self.username,
                password=self.password,
                dsn=self.dsn
            )
            print("Successfully connected to Oracle Database")
            return True
        except oracledb.DatabaseError as e:
            print("Connection failed:", e)
            return False

    def create_tables(self):
        if not self.connection:
            print("No database connection")
            return False

        try:
            with self.connection.cursor() as cursor:
                # Create BANKS table if not exists
                cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE banks (
                        bank_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        bank_name VARCHAR2(100) NOT NULL,
                        app_name VARCHAR2(100),
                        current_rating NUMBER(3,1),
                        last_updated DATE,
                        aliases VARCHAR2(200),
                        play_store_id VARCHAR2(100)
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL; -- table already exists
                        ELSE RAISE;
                        END IF;
                END;
                """)

                # Create REVIEWS table if not exists
                cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE reviews (
                        review_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        bank_id NUMBER REFERENCES banks(bank_id),
                        review_text VARCHAR2(4000),
                        rating NUMBER(1) CHECK (rating BETWEEN 1 AND 5),
                        sentiment_score NUMBER(5,3),
                        sentiment_label VARCHAR2(20),
                        themes VARCHAR2(200),
                        review_date DATE,
                        source VARCHAR2(50) DEFAULT ''Google Play''
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL; -- table already exists
                        ELSE RAISE;
                        END IF;
                END;
                """)

                # Create indexes if not exists
                cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE INDEX idx_reviews_bank_id ON reviews(bank_id)';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL; -- index already exists
                        ELSE RAISE;
                        END IF;
                END;
                """)

                cursor.execute("""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE INDEX idx_reviews_sentiment ON reviews(sentiment_label)';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL; -- index already exists
                        ELSE RAISE;
                        END IF;
                END;
                """)

                self.connection.commit()
                print("Tables and indexes verified/created")
                return True
        except oracledb.DatabaseError as e:
            print("Error creating tables:", e)
            self.connection.rollback()
            return False

    def initialize_banks(self):
        if not self.connection:
            print("No database connection")
            return False

        banks = [
            ("Commercial Bank of Ethiopia", "Commercial bank of Ethiopia Mobile", 4.4,
             "combanketh,commercial bank,cbe,commercial bank of ethiopia", "com.combanketh.mobilebanking"),
            ("Bank of Abyssinia", "Bank of Abyssinia Mobile", 2.8,
             "boa,abyssinia,bank of abyssinia", "com.boa.boaMobileBanking"),
            ("Dashen Bank", "Dashen Bank Mobile", 4.0,
             "dashen,dashen bank", "com.dashen.dashensuperapp")
        ]

        try:
            with self.connection.cursor() as cursor:
                # First clear existing data for fresh start
                cursor.execute("DELETE FROM reviews")
                cursor.execute("DELETE FROM banks")
                
                # Insert fresh bank data
                cursor.executemany("""
                INSERT INTO banks (bank_name, app_name, current_rating, last_updated, aliases, play_store_id)
                VALUES (:1, :2, :3, SYSDATE, :4, :5)
                """, banks)
                
                self.connection.commit()
                print(f"Initialized {len(banks)} banks successfully")
                return True
        except oracledb.DatabaseError as e:
            print("Error initializing banks:", e)
            self.connection.rollback()
            return False

    def find_bank_id(self, bank_name):
        """Improved bank name matching with fuzzy logic"""
        if not self.connection:
            print("No database connection")
            return None

        try:
            with self.connection.cursor() as cursor:
                # First try exact match
                cursor.execute("""
                SELECT bank_id FROM banks 
                WHERE LOWER(bank_name) = LOWER(:1)
                   OR LOWER(app_name) = LOWER(:1)
                   OR :1 LIKE '%' || LOWER(bank_name) || '%'
                   OR :1 LIKE '%' || LOWER(app_name) || '%'
                """, [bank_name.lower()])
                row = cursor.fetchone()
                if row:
                    return row[0]

                # Then try matching against aliases
                cursor.execute("""
                SELECT bank_id FROM banks 
                WHERE ',' || LOWER(aliases) || ',' LIKE '%,' || LOWER(:1) || ',%'
                """, [bank_name.lower()])
                row = cursor.fetchone()
                if row:
                    return row[0]

                # Try matching parts of the name
                cursor.execute("SELECT bank_id, bank_name, aliases FROM banks")
                for bank_id, db_bank_name, aliases in cursor:
                    db_bank_name = db_bank_name.lower()
                    if db_bank_name in bank_name.lower() or bank_name.lower() in db_bank_name:
                        return bank_id
                    if aliases:
                        for alias in [a.strip().lower() for a in aliases.split(',')]:
                            if alias in bank_name.lower() or bank_name.lower() in alias:
                                return bank_id

                print(f"No matching bank found for: {bank_name}")
                return None
        except oracledb.DatabaseError as e:
            print("Error finding bank:", e)
            return None

    def insert_reviews(self, df_reviews):
        if not self.connection:
            print("No database connection")
            return False

        try:
            with self.connection.cursor() as cursor:
                # First verify we have banks
                cursor.execute("SELECT COUNT(*) FROM banks")
                if cursor.fetchone()[0] == 0:
                    print("No banks found in database")
                    return False

                data_to_insert = []
                unmatched_banks = set()

                for _, row in df_reviews.iterrows():
                    bank_name = str(row['bank']).strip()
                    bank_id = self.find_bank_id(bank_name)

                    if not bank_id:
                        unmatched_banks.add(bank_name)
                        continue

                    review_text = str(row['review'])[:4000]  # Limit for VARCHAR2
                    rating = int(row['rating'])
                    review_date = row['date']
                    
                    if isinstance(review_date, str):
                        try:
                            review_date = datetime.strptime(review_date, '%Y-%m-%d')
                        except ValueError:
                            review_date = datetime.now()
                    elif pd.isnull(review_date):
                        review_date = datetime.now()

                    data_to_insert.append((
                        bank_id, review_text, rating, 
                        row.get('sentiment_score'), 
                        row.get('sentiment_label'), 
                        row.get('themes'), 
                        review_date, 
                        str(row.get('source', 'Google Play'))
                    ))

                if unmatched_banks:
                    print(f"Warning: Could not match these bank names: {unmatched_banks}")

                if not data_to_insert:
                    print("No valid reviews to insert")
                    return False

                # Insert in batches
                batch_size = 100
                total_inserted = 0
                for i in range(0, len(data_to_insert), batch_size):
                    cursor.executemany("""
                    INSERT INTO reviews (
                        bank_id, review_text, rating, sentiment_score, 
                        sentiment_label, themes, review_date, source
                    ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
                    """, data_to_insert[i:i+batch_size])
                    self.connection.commit()
                    total_inserted += len(data_to_insert[i:i+batch_size])
                    print(f"Inserted batch {i//batch_size + 1}: {total_inserted} total reviews")

                print(f"Successfully inserted {total_inserted} reviews")
                return True

        except oracledb.DatabaseError as e:
            print("Error inserting reviews:", e)
            self.connection.rollback()
            return False
        except Exception as e:
            print("Unexpected error:", e)
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def main():
    # Configuration
    DB_USER = "SYSTEM"
    DB_PASSWORD = "oracar123"
    CSV_PATH = "../data/ethiopian_bank_reviews_400_each.csv"

    # Initialize database manager
    db_manager = OracleDBManager(DB_USER, DB_PASSWORD)

    try:
        if not db_manager.connect():
            print("Failed to connect to database")
            return

        # Initialize database structure
        if not db_manager.create_tables():
            print("Failed to create tables")
            return

        # Reset and populate bank data
        if not db_manager.initialize_banks():
            print("Failed to initialize banks")
            return

        # Load and process reviews
        try:
            df_reviews = pd.read_csv(CSV_PATH)
            print(f"Loaded {len(df_reviews)} reviews from {CSV_PATH}")

            # Validate required columns
            required_columns = ['review', 'rating', 'date', 'bank']
            if not all(col in df_reviews.columns for col in required_columns):
                missing = set(required_columns) - set(df_reviews.columns)
                raise ValueError(f"CSV missing required columns: {missing}")

            # Clean and standardize data
            df_reviews['bank'] = df_reviews['bank'].str.strip()
            df_reviews['review'] = df_reviews['review'].str.strip()
            df_reviews['date'] = pd.to_datetime(df_reviews['date'], errors='coerce')
            df_reviews['date'] = df_reviews['date'].fillna(pd.to_datetime('today'))
            df_reviews['source'] = df_reviews.get('source', 'Google Play')

            # Insert reviews
            if not db_manager.insert_reviews(df_reviews):
                print("Failed to insert reviews")
                return

        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return

    finally:
        db_manager.close()

if __name__ == "__main__":
    main()