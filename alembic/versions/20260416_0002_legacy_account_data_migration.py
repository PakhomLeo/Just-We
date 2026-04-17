"""legacy account data migration

Revision ID: 20260416_0002
Revises: 20260416_0001
Create Date: 2026-04-16 18:30:00
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from alembic import op
import sqlalchemy as sa


revision = "20260416_0002"
down_revision = "20260416_0001"
branch_labels = None
depends_on = None


LEGACY_INTERVAL_HOURS_BY_TIER = {
    1: 24,
    2: 48,
    3: 72,
    4: 144,
    5: 336,
}


def _lower_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _normalize_old_account_type(value: object) -> str:
    normalized = _lower_text(value)
    if normalized == "weread":
        return "weread"
    return "mp_admin"


def _map_collector_status(status: object, health_status: object) -> str:
    status_norm = _lower_text(status)
    health_norm = _lower_text(health_status)
    if health_norm in {"expired", "invalid"}:
        return "expired"
    if status_norm in {"inactive", "disabled"}:
        return "disabled"
    if status_norm == "blocked":
        return "error"
    return "active"


def _map_collector_health(health_status: object) -> str:
    normalized = _lower_text(health_status)
    if normalized in {"normal", "restricted", "expired", "invalid"}:
        return normalized
    return "normal"


def _map_risk_status(status: object, health_status: object) -> str:
    status_norm = _lower_text(status)
    health_norm = _lower_text(health_status)
    if status_norm == "blocked":
        return "blocked"
    if health_norm == "restricted":
        return "cooling"
    return "normal"


def _map_monitored_status(status: object, health_status: object) -> str:
    status_norm = _lower_text(status)
    health_norm = _lower_text(health_status)
    if health_norm == "restricted":
        return "risk_observed"
    if health_norm == "invalid" or status_norm == "blocked":
        return "invalid"
    if status_norm in {"inactive", "disabled"}:
        return "paused"
    return "monitoring"


def _fallback_fetch_mode(primary_fetch_mode: str) -> str:
    return "weread" if primary_fetch_mode == "mp_admin" else "mp_admin"


def _canonical_source_url(biz: object, fakeid: object) -> str:
    biz_text = str(biz or "").strip()
    fakeid_text = str(fakeid or "").strip()
    if biz_text:
        return f"https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz_text}"
    if fakeid_text:
        return f"https://mp.weixin.qq.com/mp/profile_ext?action=home&fakeid={fakeid_text}"
    return "https://mp.weixin.qq.com/"


def _build_collector_credentials(row: Mapping[str, object]) -> dict[str, object]:
    cookies = row.get("cookies")
    payload: dict[str, object] = {}
    if isinstance(cookies, Mapping):
        payload["cookies"] = dict(cookies)
    elif cookies is not None:
        payload["cookies"] = cookies
    if row.get("biz"):
        payload["biz"] = row["biz"]
    if row.get("fakeid"):
        payload["fakeid"] = row["fakeid"]
    if row.get("name"):
        payload["legacy_name"] = row["name"]
    payload["legacy_account_id"] = row["id"]
    return payload


def _build_collector_metadata(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "legacy_migration": {
            "source_table": "accounts",
            "legacy_account_id": row["id"],
            "legacy_status": _lower_text(row.get("status")),
            "legacy_health_status": _lower_text(row.get("health_status")),
        },
        "biz": row.get("biz"),
        "fakeid": row.get("fakeid"),
        "health_reason": row.get("health_reason"),
    }


def _build_monitored_strategy_config(row: Mapping[str, object], primary_fetch_mode: str) -> dict[str, object]:
    return {
        "legacy_migration": {
            "source_table": "accounts",
            "legacy_account_id": row["id"],
        },
        "legacy_account_type": _lower_text(row.get("account_type")),
        "primary_fetch_mode_source": primary_fetch_mode,
    }


def _should_create_collector(row: Mapping[str, object]) -> bool:
    return any(
        (
            row.get("cookies") is not None,
            row.get("cookies_expire_at") is not None,
            row.get("last_health_check") is not None,
            row.get("health_reason") not in (None, ""),
        )
    )


def _select_default_owner_user_id(connection) -> object:
    candidates = connection.execute(
        sa.text(
            """
            SELECT id
            FROM users
            ORDER BY
                CASE
                    WHEN lower(CAST(role AS TEXT)) IN ('admin', 'superuser') THEN 0
                    WHEN is_superuser THEN 0
                    WHEN is_active THEN 1
                    ELSE 2
                END,
                id ASC
            LIMIT 1
            """
        )
    ).scalar()
    if candidates is None:
        raise RuntimeError(
            "Legacy account migration requires at least one user row to populate "
            "collector_accounts.owner_user_id and monitored_accounts.owner_user_id."
        )
    return candidates


def _compute_next_scheduled_at(last_checked, current_tier: int):
    if last_checked is None:
        return None
    return last_checked + timedelta(hours=LEGACY_INTERVAL_HOURS_BY_TIER.get(current_tier, 72))


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    if "accounts" not in existing_tables:
        return

    owner_user_id = _select_default_owner_user_id(connection)
    legacy_accounts = [
        dict(row._mapping)
        for row in connection.execute(
            sa.text(
                """
                SELECT
                    id,
                    biz,
                    fakeid,
                    name,
                    account_type,
                    current_tier,
                    composite_score,
                    last_checked,
                    last_updated,
                    update_history,
                    ai_relevance_history,
                    manual_override,
                    cookies,
                    cookies_expire_at,
                    status,
                    health_status,
                    last_health_check,
                    health_reason,
                    created_at,
                    updated_at
                FROM accounts
                ORDER BY id
                """
            )
        )
    ]

    monitored_id_by_legacy_id: dict[int, int] = {}

    monitored_insert_sql = sa.text(
        """
        INSERT INTO monitored_accounts (
            owner_user_id,
            biz,
            fakeid,
            name,
            source_url,
            avatar_url,
            current_tier,
            composite_score,
            primary_fetch_mode,
            fallback_fetch_mode,
            status,
            last_polled_at,
            last_published_at,
            next_scheduled_at,
            update_history,
            ai_relevance_history,
            manual_override,
            strategy_config,
            created_at,
            updated_at
        ) VALUES (
            :owner_user_id,
            :biz,
            :fakeid,
            :name,
            :source_url,
            NULL,
            :current_tier,
            :composite_score,
            :primary_fetch_mode,
            :fallback_fetch_mode,
            :status,
            :last_polled_at,
            :last_published_at,
            :next_scheduled_at,
            :update_history,
            :ai_relevance_history,
            :manual_override,
            :strategy_config,
            :created_at,
            :updated_at
        )
        ON CONFLICT (biz) DO UPDATE SET
            fakeid = COALESCE(EXCLUDED.fakeid, monitored_accounts.fakeid),
            name = EXCLUDED.name,
            source_url = COALESCE(monitored_accounts.source_url, EXCLUDED.source_url),
            current_tier = EXCLUDED.current_tier,
            composite_score = EXCLUDED.composite_score,
            primary_fetch_mode = EXCLUDED.primary_fetch_mode,
            fallback_fetch_mode = EXCLUDED.fallback_fetch_mode,
            status = EXCLUDED.status,
            last_polled_at = COALESCE(EXCLUDED.last_polled_at, monitored_accounts.last_polled_at),
            last_published_at = COALESCE(EXCLUDED.last_published_at, monitored_accounts.last_published_at),
            next_scheduled_at = COALESCE(EXCLUDED.next_scheduled_at, monitored_accounts.next_scheduled_at),
            update_history = EXCLUDED.update_history,
            ai_relevance_history = EXCLUDED.ai_relevance_history,
            manual_override = EXCLUDED.manual_override,
            strategy_config = EXCLUDED.strategy_config,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """
    ).bindparams(
        sa.bindparam("update_history", type_=sa.JSON()),
        sa.bindparam("ai_relevance_history", type_=sa.JSON()),
        sa.bindparam("manual_override", type_=sa.JSON()),
        sa.bindparam("strategy_config", type_=sa.JSON()),
    )

    collector_insert_sql = sa.text(
        """
        INSERT INTO collector_accounts (
            owner_user_id,
            account_type,
            display_name,
            external_id,
            credentials,
            status,
            health_status,
            expires_at,
            last_health_check,
            last_success_at,
            last_failure_at,
            risk_status,
            risk_reason,
            metadata_json,
            created_at,
            updated_at
        )
        SELECT
            :owner_user_id,
            :account_type,
            :display_name,
            :external_id,
            :credentials,
            :status,
            :health_status,
            :expires_at,
            :last_health_check,
            :last_success_at,
            :last_failure_at,
            :risk_status,
            :risk_reason,
            :metadata_json,
            :created_at,
            :updated_at
        WHERE NOT EXISTS (
            SELECT 1
            FROM collector_accounts
            WHERE metadata_json -> 'legacy_migration' ->> 'legacy_account_id' = :legacy_account_id
        )
        """
    ).bindparams(
        sa.bindparam("credentials", type_=sa.JSON()),
        sa.bindparam("metadata_json", type_=sa.JSON()),
    )

    for row in legacy_accounts:
        primary_fetch_mode = _normalize_old_account_type(row.get("account_type"))
        current_tier = int(row.get("current_tier") or 3)
        current_tier = current_tier if current_tier in LEGACY_INTERVAL_HOURS_BY_TIER else 3
        next_scheduled_at = _compute_next_scheduled_at(row.get("last_checked"), current_tier)

        monitored_id = connection.execute(
            monitored_insert_sql,
            {
                "owner_user_id": owner_user_id,
                "biz": row.get("biz") or f"legacy_biz_{row['id']}",
                "fakeid": row.get("fakeid"),
                "name": row.get("name") or f"Legacy Monitored {row['id']}",
                "source_url": _canonical_source_url(row.get("biz"), row.get("fakeid")),
                "current_tier": current_tier,
                "composite_score": float(row.get("composite_score") or 50.0),
                "primary_fetch_mode": primary_fetch_mode,
                "fallback_fetch_mode": _fallback_fetch_mode(primary_fetch_mode),
                "status": _map_monitored_status(row.get("status"), row.get("health_status")),
                "last_polled_at": row.get("last_checked"),
                "last_published_at": row.get("last_updated"),
                "next_scheduled_at": next_scheduled_at,
                "update_history": row.get("update_history") or {},
                "ai_relevance_history": row.get("ai_relevance_history") or {},
                "manual_override": row.get("manual_override"),
                "strategy_config": _build_monitored_strategy_config(row, primary_fetch_mode),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            },
        ).scalar_one()
        monitored_id_by_legacy_id[int(row["id"])] = int(monitored_id)

        if _should_create_collector(row):
            connection.execute(
                collector_insert_sql,
                {
                    "owner_user_id": owner_user_id,
                    "account_type": primary_fetch_mode,
                    "display_name": row.get("name") or f"Legacy Collector {row['id']}",
                    "external_id": row.get("fakeid") or row.get("biz") or f"legacy_account_{row['id']}",
                    "credentials": _build_collector_credentials(row),
                    "status": _map_collector_status(row.get("status"), row.get("health_status")),
                    "health_status": _map_collector_health(row.get("health_status")),
                    "expires_at": row.get("cookies_expire_at"),
                    "last_health_check": row.get("last_health_check"),
                    "last_success_at": row.get("last_checked") or row.get("updated_at"),
                    "last_failure_at": row.get("last_health_check")
                    if _map_collector_status(row.get("status"), row.get("health_status")) != "active"
                    else None,
                    "risk_status": _map_risk_status(row.get("status"), row.get("health_status")),
                    "risk_reason": row.get("health_reason"),
                    "metadata_json": _build_collector_metadata(row),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "legacy_account_id": str(row["id"]),
                },
            )

    for legacy_account_id, monitored_account_id in monitored_id_by_legacy_id.items():
        connection.execute(
            sa.text(
                """
                UPDATE articles
                SET monitored_account_id = :monitored_account_id
                WHERE account_id = :legacy_account_id
                  AND monitored_account_id IS NULL
                """
            ),
            {
                "legacy_account_id": legacy_account_id,
                "monitored_account_id": monitored_account_id,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())

    if "articles" in existing_tables:
        connection.execute(sa.text("UPDATE articles SET monitored_account_id = NULL"))

    if "collector_accounts" in existing_tables:
        connection.execute(
            sa.text(
                """
                DELETE FROM collector_accounts
                WHERE metadata_json -> 'legacy_migration' ->> 'source_table' = 'accounts'
                """
            )
        )

    if "monitored_accounts" in existing_tables:
        connection.execute(
            sa.text(
                """
                DELETE FROM monitored_accounts
                WHERE strategy_config -> 'legacy_migration' ->> 'source_table' = 'accounts'
                """
            )
        )
