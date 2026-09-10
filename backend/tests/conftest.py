import os
import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.vendor import Vendor

@pytest.fixture(autouse=True)
async def cleanup_test_vendors_after_test():
    """Ensures test vendors created with randomized test domains are cleaned up after each test."""
    yield
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Vendor)
            res = await session.execute(stmt)
            vendors = res.scalars().all()
            for v in vendors:
                # Identify test domains created by pytest fixtures
                if any(tag in v.domain for tag in [
                    "-api-", "fail-", "success-", "unchanged-", "changed-",
                    "empty-", "acme-", "slack-", "stripe-", "mock-", "test-",
                    "-iso-", "v1-iso-", "v2-iso-", "iso-"
                ]):
                    await session.delete(v)
            await session.commit()
    except Exception:
        pass
