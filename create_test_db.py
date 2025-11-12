"""
Script to create and set up the test database.
Run this before running tests.
"""
import asyncio
import asyncpg
import os
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.session import Base

# Database connection parameters - use environment variables if available (for Docker)
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("TEST_DB_NAME", "communityhub_test")

async def create_database():
    """Create the test database if it doesn't exist."""
    # Connect to the default 'postgres' database to create our test database
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database='postgres'
        )
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            DB_NAME
        )
        
        if not exists:
            # Create the database
            await conn.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"✅ Database '{DB_NAME}' created successfully")
        else:
            print(f"ℹ️  Database '{DB_NAME}' already exists")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False
    
    return True

async def create_tables():
    """Create all tables in the test database."""
    try:
        # Create engine for the test database
        engine = create_async_engine(
            f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            echo=False
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Tables created successfully")
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

async def main():
    """Main setup function."""
    print("🔧 Setting up test database...")
    print()
    
    if not await create_database():
        return
    
    if not await create_tables():
        return
    
    print()
    print("✅ Test database setup complete!")
    print(f"   Database: {DB_NAME}")
    print(f"   Host: {DB_HOST}:{DB_PORT}")
    print(f"   User: {DB_USER}")
    print()
    print("You can now run tests with: pytest")

if __name__ == "__main__":
    asyncio.run(main())
