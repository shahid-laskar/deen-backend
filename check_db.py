import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check():
    print("Starting DB check...")
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(User).limit(1))
            print("✓ Database connection and User table OK")
            users = res.scalars().all()
            print(f"Found {len(users)} users.")
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check())
