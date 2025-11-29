"""
Display database schema from SQLAlchemy models
"""
from sqlalchemy import inspect
from models.user_db import UserDB
from models.device_db import DeviceDB

print('=' * 80)
print('DATABASE SCHEMA - From SQLAlchemy Models')
print('=' * 80)
print()

models = [
    ('users', UserDB),
    ('devices', DeviceDB),
]

for table_name, model_class in models:
    print(f'📋 TABLE: {table_name}')
    print('-' * 80)
    
    # Get mapper
    mapper = inspect(model_class)
    
    # Get columns
    for column in mapper.columns:
        col_name = column.name
        col_type = str(column.type)
        nullable = 'NULL' if column.nullable else 'NOT NULL'
        primary_key = ' 🔑 PRIMARY KEY' if column.primary_key else ''
        foreign_keys = ''
        if column.foreign_keys:
            fk = list(column.foreign_keys)[0]
            foreign_keys = f' 🔗 FK -> {fk.column}'
        
        print(f'  • {col_name:30s} {col_type:20s} {nullable}{primary_key}{foreign_keys}')
    
    print()

print('=' * 80)
print()
print('💡 TIP: To see actual data counts and indexes, run this from Render Shell:')
print('   1. Go to Render Dashboard → Your PostgreSQL database')
print('   2. Click "Shell" tab')
print('   3. Run: \\dt  (to list tables)')
print('   4. Run: \\d users  (to describe users table)')
print('   5. Run: SELECT * FROM users LIMIT 5;  (to see data)')
print()

