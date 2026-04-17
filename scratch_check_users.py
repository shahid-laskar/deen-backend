import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.email, User.role))
        users = result.all()
        for email, role in users:
            print(f"User: {email}, Role: {role}")

if __name__ == "__main__":
    asyncio.run(check_users())
