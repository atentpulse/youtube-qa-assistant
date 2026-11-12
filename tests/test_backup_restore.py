"""
Tests for YtGenius PostgreSQL Backup and Restore Utilities (Phase 3C Task 2).
Verifies:
- Safe connection URL parsing
- Timestamped filename generation and atomic temporary file handling
- Credential safety (PGPASSWORD environment passing, never CLI arguments, redaction in errors)
- Retention pruning logic
- Safety guards against accidental overwrite of active/production databases
- Archive integrity TOC inspection
- Post-restore schema verification (tables, Alembic head, PK/FK counts)
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure scripts directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.backup_db as backup_db
import scripts.restore_db as restore_db


class TestParseDbUrl:
    """Test URL parsing for backup and restore scripts."""

    def test_parse_full_url(self):
        url = "postgresql://myuser:secret123@db.example.com:5433/custom_db"
        params = backup_db.parse_db_url(url)
        assert params["user"] == "myuser"
        assert params["password"] == "secret123"
        assert params["host"] == "db.example.com"
        assert params["port"] == "5433"
        assert params["dbname"] == "custom_db"

    def test_parse_default_fallbacks(self):
        url = "postgresql://localhost/test_db"
        params = backup_db.parse_db_url(url)
        assert params["user"] == "ytgenius"
        assert params["password"] == ""
        assert params["host"] == "localhost"
        assert params["port"] == "5432"
        assert params["dbname"] == "test_db"

    def test_restore_script_parse_url_identical(self):
        url = "postgresql://app_user:pass456@10.0.0.1:5432/ytgenius_staging"
        b_params = backup_db.parse_db_url(url)
        r_params = restore_db.parse_db_url(url)
        assert b_params == r_params


class TestRetentionPruning:
    """Test retention pruning for backup files."""

    def test_prune_old_backups(self, tmp_path):
        # Create 5 simulated backup files with staggered modification times
        files = [
            tmp_path / "ytgenius_backup_20261112_010000.dump",
            tmp_path / "ytgenius_backup_20261112_020000.dump",
            tmp_path / "ytgenius_backup_20261112_030000.dump",
            tmp_path / "ytgenius_backup_20261112_040000.dump",
            tmp_path / "ytgenius_backup_20261112_050000.dump",
        ]
        for idx, f in enumerate(files):
            f.write_text("data")
            # Set explicit mtime
            os.utime(f, (1000 + idx * 100, 1000 + idx * 100))

        # Also create a non-matching custom file that should NEVER be pruned
        custom_file = tmp_path / "manual_export.dump"
        custom_file.write_text("custom")
        os.utime(custom_file, (500, 500))

        # Keep latest 3
        pruned = backup_db.prune_old_backups(tmp_path, keep_count=3)

        assert len(pruned) == 2
        assert "ytgenius_backup_20261112_010000.dump" in pruned
        assert "ytgenius_backup_20261112_020000.dump" in pruned

        # Verify remaining files
        remaining = [f.name for f in tmp_path.iterdir()]
        assert "ytgenius_backup_20261112_030000.dump" in remaining
        assert "ytgenius_backup_20261112_040000.dump" in remaining
        assert "ytgenius_backup_20261112_050000.dump" in remaining
        assert "manual_export.dump" in remaining

    def test_prune_with_zero_or_negative_keep(self, tmp_path):
        f = tmp_path / "ytgenius_backup_20261112_010000.dump"
        f.write_text("data")
        pruned = backup_db.prune_old_backups(tmp_path, keep_count=0)
        assert pruned == []
        assert f.exists()


class TestBackupExecutionSafety:
    """Test credential isolation, command building, and atomic writing in backup_db."""

    @patch("subprocess.run")
    def test_backup_passes_password_via_env_not_cli_args(self, mock_run, tmp_path):
        # Mock successful subprocess
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        db_url = "postgresql://ytgenius:SUPER_SECRET_PW@127.0.0.1:5432/ytgenius_test"
        filename = "test_atomic.dump"

        # Side effect to create non-empty temp file so atomic check passes
        def fake_run(cmd, *args, **kwargs):
            # Check credentials not in cmd arguments
            for arg in cmd:
                assert "SUPER_SECRET_PW" not in str(arg), f"Secret leaked in CLI argument: {arg}"

            temp_f = tmp_path / f".tmp_{filename}"
            temp_f.write_bytes(b"PG_DUMP_HEADER_DATA")
            return mock_proc

        mock_run.side_effect = fake_run

        with patch("shutil.which", return_value="/usr/bin/pg_dump"):
            backup_file = backup_db.run_backup(
                db_url=db_url,
                output_dir=str(tmp_path),
                filename=filename,
            )

        assert backup_file.name == filename
        assert backup_file.exists()
        assert not (tmp_path / f".tmp_{filename}").exists()

        # Check that PGPASSWORD was passed in kwargs['env']
        env_passed = mock_run.call_args[1].get("env", {})
        assert env_passed.get("PGPASSWORD") == "SUPER_SECRET_PW"

    @patch("subprocess.run")
    def test_backup_redacts_password_on_failure(self, mock_run, tmp_path):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b"Connection to 127.0.0.1:5432 failed with password SUPER_SECRET_PW"
        mock_run.return_value = mock_proc

        db_url = "postgresql://ytgenius:SUPER_SECRET_PW@127.0.0.1:5432/ytgenius_test"

        with patch("shutil.which", return_value="/usr/bin/pg_dump"):
            with pytest.raises(RuntimeError) as exc_info:
                backup_db.run_backup(
                    db_url=db_url,
                    output_dir=str(tmp_path),
                    filename="fail.dump",
                )

            err_msg = str(exc_info.value)
            assert "SUPER_SECRET_PW" not in err_msg
            assert "[REDACTED]" in err_msg


class TestRestoreSafetyGuards:
    """Test safety blocks and integrity checks in restore_db."""

    def test_restore_rejects_active_database_without_force(self, tmp_path):
        dummy_dump = tmp_path / "valid.dump"
        dummy_dump.write_bytes(b"DUMP_CONTENT")

        # Target database matches DATABASE_URL database
        with pytest.raises(PermissionError) as exc_info:
            restore_db.run_restore(
                backup_path=str(dummy_dump),
                target_db="ytgenius",
                db_url="postgresql://ytgenius:pw@127.0.0.1:5432/ytgenius",
                force=False,
            )
        assert "SAFETY BLOCK" in str(exc_info.value)
        assert "--force" in str(exc_info.value)

    def test_restore_rejects_missing_or_empty_file(self, tmp_path):
        # Non-existent file
        with pytest.raises(FileNotFoundError):
            restore_db.run_restore(
                backup_path=str(tmp_path / "does_not_exist.dump"),
                target_db="ytgenius_restored",
            )

        # Empty file
        empty_dump = tmp_path / "empty.dump"
        empty_dump.write_bytes(b"")
        with pytest.raises(ValueError, match="empty"):
            restore_db.run_restore(
                backup_path=str(empty_dump),
                target_db="ytgenius_restored",
            )

    @patch("subprocess.run")
    def test_inspect_archive_toc(self, mock_run, tmp_path):
        valid_dump = tmp_path / "test.dump"
        valid_dump.write_bytes(b"VALID_DUMP")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            b"; Archive created by pg_dump\n"
            b"; Archive entry 1\n"
            b"215; 1259 16400 TABLE public users ytgenius\n"
            b"216; 1259 16410 TABLE public videos ytgenius\n"
        )
        mock_run.return_value = mock_proc

        with patch("shutil.which", return_value="/usr/bin/pg_restore"):
            entries = restore_db.inspect_archive(valid_dump)

        assert len(entries) == 2
        assert "users" in entries[0]
        assert "videos" in entries[1]

    def test_verify_database_integrity_validates_tables_and_alembic(self):
        # Test integrity validation logic with simulated query outputs
        params = {"user": "ytgenius", "password": "", "host": "127.0.0.1", "port": "5432"}

        with patch("subprocess.run") as mock_run:
            # 1. tables query
            mock_proc_tables = MagicMock(returncode=0, stdout="\n".join(restore_db.EXPECTED_TABLES))
            # 2. alembic query
            mock_proc_alembic = MagicMock(returncode=0, stdout="a1b2c3d4e5f6\n")
            # 3. pk count
            mock_proc_pk = MagicMock(returncode=0, stdout="12\n")
            # 4. fk count
            mock_proc_fk = MagicMock(returncode=0, stdout="11\n")

            mock_run.side_effect = [
                mock_proc_tables,
                mock_proc_alembic,
                mock_proc_pk,
                mock_proc_fk,
            ]

            with patch("shutil.which", return_value="/usr/bin/psql"):
                result = restore_db.verify_database_integrity("ytgenius_restored", params)

            assert result["alembic_version"] == "a1b2c3d4e5f6"
            assert result["table_count"] == len(restore_db.EXPECTED_TABLES)
            assert result["primary_keys"] == 12
            assert result["foreign_keys"] == 11

    def test_verify_database_integrity_detects_missing_table(self):
        params = {"user": "ytgenius", "password": "", "host": "127.0.0.1", "port": "5432"}

        with patch("subprocess.run") as mock_run:
            # Missing 'conversations' table
            tables = [t for t in restore_db.EXPECTED_TABLES if t != "conversations"]
            mock_proc_tables = MagicMock(returncode=0, stdout="\n".join(tables))
            mock_proc_alembic = MagicMock(returncode=0, stdout="a1b2c3d4e5f6\n")
            mock_proc_pk = MagicMock(returncode=0, stdout="11\n")
            mock_proc_fk = MagicMock(returncode=0, stdout="9\n")

            mock_run.side_effect = [
                mock_proc_tables,
                mock_proc_alembic,
                mock_proc_pk,
                mock_proc_fk,
            ]

            with patch("shutil.which", return_value="/usr/bin/psql"):
                with pytest.raises(ValueError, match="missing expected table"):
                    restore_db.verify_database_integrity("ytgenius_restored", params)

    def test_verify_database_integrity_detects_wrong_alembic_head(self):
        params = {"user": "ytgenius", "password": "", "host": "127.0.0.1", "port": "5432"}

        with patch("subprocess.run") as mock_run:
            mock_proc_tables = MagicMock(returncode=0, stdout="\n".join(restore_db.EXPECTED_TABLES))
            # Outdated migration
            mock_proc_alembic = MagicMock(returncode=0, stdout="old_revision_123\n")
            mock_proc_pk = MagicMock(returncode=0, stdout="12\n")
            mock_proc_fk = MagicMock(returncode=0, stdout="11\n")

            mock_run.side_effect = [
                mock_proc_tables,
                mock_proc_alembic,
                mock_proc_pk,
                mock_proc_fk,
            ]

            with patch("shutil.which", return_value="/usr/bin/psql"):
                with pytest.raises(ValueError, match="does not match expected head"):
                    restore_db.verify_database_integrity("ytgenius_restored", params)
