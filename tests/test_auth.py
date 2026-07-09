"""Tests for field-level encryption at rest (Phase 5)."""

from __future__ import annotations

from cryptography.fernet import Fernet

from discern.api import auth
from discern.config import settings


def test_encrypt_field_roundtrips_with_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "field_encryption_key", Fernet.generate_key().decode())
    auth._fernet_checked = False
    auth._fernet_instance = None

    ciphertext = auth.encrypt_field("please pray for my mother")
    assert ciphertext != "please pray for my mother"
    assert auth.decrypt_field(ciphertext) == "please pray for my mother"


def test_encrypt_field_returns_plaintext_without_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "field_encryption_key", "")
    auth._fernet_checked = False
    auth._fernet_instance = None

    assert auth.encrypt_field("please pray for my mother") == "please pray for my mother"
    assert auth.decrypt_field("please pray for my mother") == "please pray for my mother"
