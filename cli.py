import asyncio
import argparse
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def set_admin(email: str, make_admin: bool = True):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"Error: User with email '{email}' not found.")
            return

        user.role = "admin" if make_admin else "user"
        await session.commit()
        
        print(f"Success: User {email} role set to '{user.role}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deen App Admin Management CLI")
    parser.add_argument("email", type=str, help="Email of the user to promote/demote")
    parser.add_argument("--revoke", action="store_true", help="Revoke admin privileges")
    
    args = parser.parse_args()
    
    asyncio.run(set_admin(args.email, make_admin=not args.revoke))
