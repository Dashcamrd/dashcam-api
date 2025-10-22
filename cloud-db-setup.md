# Cloud Database Setup Guide

## Option 1: Railway (Recommended)

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Create new project

### Step 2: Add MySQL Database
1. Click "New" → "Database" → "MySQL"
2. Wait for database to provision
3. Go to "Variables" tab
4. Copy the connection details

### Step 3: Get Connection String
Railway will provide:
- `MYSQL_URL` (full connection string)
- `MYSQL_HOST`
- `MYSQL_PORT` 
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

## Option 2: PlanetScale

### Step 1: Create Account
1. Go to https://planetscale.com
2. Sign up with GitHub
3. Create new database

### Step 2: Get Connection Details
1. Go to your database
2. Click "Connect"
3. Copy connection string

## Option 3: Supabase (PostgreSQL)

### Step 1: Create Project
1. Go to https://supabase.com
2. Create new project
3. Go to Settings → Database
4. Copy connection string

## Environment Configuration

Update your `.env` file with cloud database URL:

```bash
# For Railway/PlanetScale (MySQL)
DATABASE_URL=mysql+pymysql://username:password@host:port/database

# For Supabase (PostgreSQL) 
DATABASE_URL=postgresql://username:password@host:port/database
```

## Migration Steps

1. Export current data:
```bash
mysqldump -u root -p dashcamdb > backup.sql
```

2. Import to cloud database:
```bash
mysql -h cloud-host -u username -p database_name < backup.sql
```

3. Update application to use cloud database
4. Test connection


