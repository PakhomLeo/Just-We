"""Tests for legacy account migration rule helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260416_0002_legacy_account_data_migration.py"
    )
    spec = spec_from_file_location("legacy_account_data_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_old_account_type_maps_mp_to_mp_admin():
    module = _load_migration_module()

    assert module._normalize_old_account_type("mp") == "mp_admin"
    assert module._normalize_old_account_type("MP") == "mp_admin"
    assert module._normalize_old_account_type("weread") == "weread"


def test_status_mapping_preserves_expired_and_blocked_semantics():
    module = _load_migration_module()

    assert module._map_collector_status("active", "expired") == "expired"
    assert module._map_collector_status("inactive", "normal") == "disabled"
    assert module._map_collector_status("blocked", "restricted") == "error"
    assert module._map_risk_status("blocked", "normal") == "blocked"
    assert module._map_risk_status("active", "restricted") == "cooling"


def test_monitored_status_mapping_prefers_health_signal():
    module = _load_migration_module()

    assert module._map_monitored_status("active", "restricted") == "risk_observed"
    assert module._map_monitored_status("blocked", "normal") == "invalid"
    assert module._map_monitored_status("inactive", "normal") == "paused"
    assert module._map_monitored_status("active", "normal") == "monitoring"


def test_collector_payloads_keep_legacy_traceability():
    module = _load_migration_module()
    row = {
        "id": 7,
        "biz": "biz_123",
        "fakeid": "fake_123",
        "name": "Legacy Account",
        "status": "active",
        "health_status": "normal",
        "health_reason": "ok",
        "cookies": {"session": "abc"},
        "account_type": "mp",
    }

    credentials = module._build_collector_credentials(row)
    metadata = module._build_collector_metadata(row)
    strategy = module._build_monitored_strategy_config(row, "mp_admin")

    assert credentials["legacy_account_id"] == 7
    assert credentials["cookies"] == {"session": "abc"}
    assert metadata["legacy_migration"]["legacy_account_id"] == 7
    assert strategy["legacy_migration"]["source_table"] == "accounts"


def test_should_create_collector_requires_credential_signal():
    module = _load_migration_module()

    assert module._should_create_collector({"cookies": {"session": "abc"}}) is True
    assert module._should_create_collector({"cookies_expire_at": "2026-04-16T00:00:00Z"}) is True
    assert module._should_create_collector({"last_health_check": "2026-04-16T00:00:00Z"}) is True
    assert module._should_create_collector({"health_reason": "expired"}) is True
    assert module._should_create_collector({"biz": "biz_123", "fakeid": "fake_123", "name": "Only monitored"}) is False
