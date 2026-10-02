"""Initialize the idempotent demo dataset without deleting existing records."""

import asyncio

from app.core.database import AsyncSessionLocal, Base, engine
from app.models import all_models  # noqa: F401
from app.services.seed import seed_database


async def main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    print("FulfillIQ demo data is ready. Existing databases were preserved.")


if __name__ == "__main__":
    asyncio.run(main())
