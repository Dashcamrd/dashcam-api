"""
Script to display all tables and columns in the database
"""
from database import engine
from sqlalchemy import text, inspect

print('=' * 80)
print('DATABASE SCHEMA - Tables and Columns')
print('=' * 80)
print()

# Get inspector
inspector = inspect(engine)

# Get all table names
tables = inspector.get_table_names()

if not tables:
    print('❌ No tables found in database')
else:
    print(f'📊 Found {len(tables)} tables:')
    print()
    
    for table_name in sorted(tables):
        print(f'📋 TABLE: {table_name}')
        print('-' * 80)
        
        # Get columns for this table
        columns = inspector.get_columns(table_name)
        
        # Print column details
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            nullable = 'NULL' if col['nullable'] else 'NOT NULL'
            default = f", DEFAULT: {col['default']}" if col.get('default') else ''
            
            print(f'  • {col_name:30s} {col_type:20s} {nullable}{default}')
        
        # Get primary keys
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk['constrained_columns']:
            pk_cols = ', '.join(pk['constrained_columns'])
            print(f'  🔑 PRIMARY KEY: {pk_cols}')
        
        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            for fk in fks:
                fk_cols = ', '.join(fk['constrained_columns'])
                ref_cols = ', '.join(fk['referred_columns'])
                print(f'  🔗 FOREIGN KEY: {fk_cols} -> {fk["referred_table"]}.{ref_cols}')
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            for idx in indexes:
                unique = 'UNIQUE ' if idx['unique'] else ''
                idx_cols = ', '.join(idx['column_names'])
                print(f'  📇 {unique}INDEX: {idx["name"]} on ({idx_cols})')
        
        # Get row count
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                count = result.scalar()
                print(f'  📊 ROWS: {count:,}')
        except:
            pass
        
        print()

print('=' * 80)

