"""Unit tests for model schema (003-edit-profile)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models.riot_account import RiotAccount
from app.models.user import User


@pytest.mark.asyncio
async def test_user_has_avatar_url_and_deleted_at_columns(db_engine):
    """T004: users table exposes avatar_url and deleted_at columns (nullable)."""
    async with db_engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {col["name"]: col for col in inspect(sync_conn).get_columns("users")}
        )

    assert "avatar_url" in columns, "users.avatar_url column missing"
    assert columns["avatar_url"]["nullable"] is True, "avatar_url must be nullable"

    assert "deleted_at" in columns, "users.deleted_at column missing"
    assert columns["deleted_at"]["nullable"] is True, "deleted_at must be nullable"


@pytest.mark.asyncio
async def test_riot_account_unique_per_user(db_session):
    """T005a: only one RiotAccount per user (UNIQUE on user_id)."""
    user_a = User(email="a@x.com", nickname="alice", password_hash="!a")
    db_session.add(user_a)
    await db_session.commit()

    db_session.add(RiotAccount(user_id=user_a.id, puuid="puuid-A", region="EUW1"))
    await db_session.commit()

    db_session.add(RiotAccount(user_id=user_a.id, puuid="puuid-A2", region="EUW1"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_riot_account_unique_puuid_across_users(db_engine):
    """T005b: same PUUID cannot belong to two users (UNIQUE on puuid)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user_a = User(email="a@x.com", nickname="alice", password_hash="!a")
        user_b = User(email="b@x.com", nickname="bob", password_hash="!b")
        session.add_all([user_a, user_b])
        await session.commit()
        a_id, b_id = user_a.id, user_b.id

    async with factory() as session:
        session.add(RiotAccount(user_id=a_id, puuid="shared-puuid", region="EUW1"))
        await session.commit()

    async with factory() as session:
        session.add(RiotAccount(user_id=b_id, puuid="shared-puuid", region="EUN1"))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_riot_account_has_uuid_id_and_linked_at(db_session):
    """RiotAccount has UUID PK and linked_at populated automatically."""
    user = User(email="z@x.com", nickname="zoe", password_hash="!z")
    db_session.add(user)
    await db_session.commit()

    acc = RiotAccount(user_id=user.id, puuid="zpuuid", region="NA1")
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    assert isinstance(acc.id, uuid.UUID)
    assert acc.linked_at is not None
