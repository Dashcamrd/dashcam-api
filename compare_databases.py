#!/usr/bin/env python3
"""
Compare two database schemas
Usage: python3 compare_databases.py <railway_url> <render_url>
"""
import sys
from sqlalchemy import create_engine, text

def get_schema(url, db_name):
    """Get schema information from a database"""
    engine = create_engine(url)
    schema = {}
    
    with engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
        
        # Get columns for each table
        for table in tables:
            result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table}' 
                ORDER BY ordinal_position;
            """))
            schema[table] = [(row[0], row[1], row[2], row[3]) for row in result]
            
            # Get row count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            schema[f"{table}_count"] = count
    
    return schema, tables

def compare_schemas(railway_url, render_url):
    """Compare two database schemas"""
    print("=" * 80)
    print("📊 DATABASE SCHEMA COMPARISON")
    print("=" * 80)
    
    print("\n🔄 Connecting to Railway database...")
    railway_schema, railway_tables = get_schema(railway_url, "Railway")
    print(f"✅ Found {len(railway_tables)} tables in Railway")
    
    print("\n🔄 Connecting to Render database...")
    render_schema, render_tables = get_schema(render_url, "Render")
    print(f"✅ Found {len(render_tables)} tables in Render")
    
    # Compare tables
    print("\n" + "=" * 80)
    print("📋 TABLE COMPARISON")
    print("=" * 80)
    
    railway_only = set(railway_tables) - set(render_tables)
    render_only = set(render_tables) - set(railway_tables)
    common = set(railway_tables) & set(render_tables)
    
    if railway_only:
        print(f"\n⚠️  Tables in Railway ONLY ({len(railway_only)}):")
        for table in railway_only:
            count = railway_schema.get(f"{table}_count", 0)
            print(f"   • {table} ({count} rows)")
    
    if render_only:
        print(f"\n⚠️  Tables in Render ONLY ({len(render_only)}):")
        for table in render_only:
            count = render_schema.get(f"{table}_count", 0)
            print(f"   • {table} ({count} rows)")
    
    print(f"\n✅ Common tables ({len(common)}):")
    for table in common:
        railway_count = railway_schema.get(f"{table}_count", 0)
        render_count = render_schema.get(f"{table}_count", 0)
        print(f"   • {table} (Railway: {railway_count} rows, Render: {render_count} rows)")
    
    # Compare columns for common tables
    print("\n" + "=" * 80)
    print("🔍 COLUMN COMPARISON")
    print("=" * 80)
    
    for table in sorted(common):
        railway_cols = {col[0]: col for col in railway_schema[table]}
        render_cols = {col[0]: col for col in render_schema[table]}
        
        railway_only_cols = set(railway_cols.keys()) - set(render_cols.keys())
        render_only_cols = set(render_cols.keys()) - set(railway_cols.keys())
        
        if railway_only_cols or render_only_cols:
            print(f"\n📄 Table: {table}")
            print("-" * 80)
            
            if railway_only_cols:
                print(f"  ⚠️  Columns in Railway ONLY:")
                for col in railway_only_cols:
                    col_info = railway_cols[col]
                    print(f"     • {col} ({col_info[1]})")
            
            if render_only_cols:
                print(f"  ⚠️  Columns in Render ONLY:")
                for col in render_only_cols:
                    col_info = render_cols[col]
                    print(f"     • {col} ({col_info[1]})")
        else:
            print(f"\n✅ Table: {table} - schemas match")
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Railway tables: {len(railway_tables)}")
    print(f"Render tables: {len(render_tables)}")
    print(f"Common tables: {len(common)}")
    print(f"Tables only in Railway: {len(railway_only)}")
    print(f"Tables only in Render: {len(render_only)}")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 compare_databases.py <railway_url> <render_url>")
        print("\nExample:")
        print('  python3 compare_databases.py \\')
        print('    "mysql://user:pass@railway.app:3306/railway" \\')
        print('    "postgresql://user:pass@render.com/renderdb"')
        sys.exit(1)
    
    railway_url = sys.argv[1]
    render_url = sys.argv[2]
    
    try:
        compare_schemas(railway_url, render_url)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

