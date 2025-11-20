-- GRAAL Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts for the first time
-- It creates the database structure and prepares for Alembic migrations
-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to automatically update updated_at timestamp
CREATE
OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $ $ BEGIN NEW.updated_at = CURRENT_TIMESTAMP;

RETURN NEW;

END;

$ $ language 'plpgsql';

-- Grant necessary permissions to graal_user
GRANT ALL PRIVILEGES ON DATABASE graal_dev TO graal_user;

GRANT ALL PRIVILEGES ON SCHEMA public TO graal_user;

-- Note: Actual table creation is handled by Alembic migrations
-- This script only sets up the environment and extensions
