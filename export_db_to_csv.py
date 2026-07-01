"""
Export SQLite database to CSV files
"""

import sqlite3
import pandas as pd
import os

def export_database_to_csv(db_path: str = "nifty_options_5years.db", output_dir: str = "."):
    """Export all tables from SQLite database to CSV files"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    
    # Get all table names
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ No tables found in database")
        conn.close()
        return
    
    print(f"📊 Found {len(tables)} tables in database:")
    print("="*70)
    
    for table_name in tables:
        table = table_name[0]
        
        # Read table into DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        
        # Create output filename
        csv_filename = f"{table}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        
        print(f"✅ {table}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   File: {csv_filename}")
        print()
    
    conn.close()
    print("="*70)
    print(f"✅ All tables exported to CSV files in: {output_dir}")
    print("\nCSV Files Created:")
    for table_name in tables:
        print(f"   - {table_name[0]}.csv")


if __name__ == "__main__":
    print("\n" + "█"*70)
    print("█" + "  DATABASE TO CSV EXPORT".center(68) + "█")
    print("█"*70 + "\n")
    
    export_database_to_csv()
