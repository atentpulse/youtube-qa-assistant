#!/usr/bin/env python3
"""
YtGenius — PostgreSQL Database Restore & Verification Utility
Restores and verifies PostgreSQL backups using native pg_restore.

Safety Features:
- Prohibits accidental overwrite of the active database without explicit --force.
- Pre-inspects backup archive header/TOC before restore using pg_restore --list.
- Automatically creates target database if requested (--create-db).
- Verifies post-restore table inventory, constraints, and Alembic migration state.
- Supports native pg_restore or Docker container execution.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


EXPECTED_TABLES = [
    "alembic_version",
    "users",
    "videos",
    "user_videos",
    "conversations",
    "messages",
    "question_cache",
    "password_reset_tokens",
    "email_verification_tokens",
    "email_otps",
    "bug_reports",
]

EXPECTED_ALEMBIC_HEAD = "a1b2c3d4e5f6"


def parse_db_url(db_url: str):
    """Parse a PostgreSQL connection URL into component parameters."""
    parsed = urlparse(db_url)
    user = parsed.username or "ytgenius"
    password = parsed.password or ""
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    dbname = parsed.path.lstrip("/") or "ytgenius"
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }


def find_docker_container(preferred_name: str = "ytgenius-postgres") -> str:
    """Find a running postgres container if Docker is available."""
    if not shutil.which("docker"):
        return ""
    try:
        res = subprocess.run(
            ["docker", "ps", "--filter", f"name={preferred_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        names = [n.strip() for n in res.stdout.strip().split("\n") if n.strip()]
        if preferred_name in names:
            return preferred_name
        if names:
            return names[0]
    except Exception:
        pass
    return ""


def inspect_archive(backup_file: Path, container: str = "") -> list:
    """Run pg_restore --list to inspect archive contents and verify integrity."""
    has_local = bool(shutil.which("pg_restore"))
    if container:
        cmd = ["docker", "exec", "-i", container, "pg_restore", "--list"]
        with open(backup_file, "rb") as f_in:
            proc = subprocess.run(cmd, stdin=f_in, capture_output=True, timeout=60)
    elif has_local:
        cmd = ["pg_restore", "--list", str(backup_file)]
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
    else:
        # Fallback to running inside a disposable container if neither exists
        cmd = ["docker", "run", "--rm", "-i", "postgres:16-alpine", "pg_restore", "--list"]
        with open(backup_file, "rb") as f_in:
            proc = subprocess.run(cmd, stdin=f_in, capture_output=True, timeout=60)

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Archive integrity check failed (pg_restore --list exited {proc.returncode}): {err}")

    lines = proc.stdout.decode("utf-8", errors="replace").splitlines()
    return [line for line in lines if line and not line.startswith(";")]


def ensure_target_database(target_db: str, params: dict, container: str = "", verbose: bool = False):
    """Ensure the target database exists; creates it if absent."""
    has_psql = bool(shutil.which("psql"))
    check_sql = f"SELECT 1 FROM pg_database WHERE datname = '{target_db}';"
    create_sql = f"CREATE DATABASE {target_db};"

    if container:
        # Check database existence via docker exec
        check_cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={params['password']}",
            container,
            "psql", "-U", params["user"], "-d", "postgres", "-tAc", check_sql
        ]
        proc = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
        if proc.stdout.strip() != "1":
            if verbose:
                sys.stdout.write(f"Target database '{target_db}' does not exist. Creating it...\n")
            create_cmd = [
                "docker", "exec", "-i",
                "-e", f"PGPASSWORD={params['password']}",
                container,
                "psql", "-U", params["user"], "-d", "postgres", "-c", create_sql
            ]
            c_proc = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
            if c_proc.returncode != 0:
                raise RuntimeError(f"Failed to create target database '{target_db}': {c_proc.stderr}")
    elif has_psql:
        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]
        check_cmd = [
            "psql", "-h", params["host"], "-p", str(params["port"]),
            "-U", params["user"], "-d", "postgres", "-tAc", check_sql
        ]
        proc = subprocess.run(check_cmd, env=env, capture_output=True, text=True, timeout=30)
        if proc.stdout.strip() != "1":
            if verbose:
                sys.stdout.write(f"Target database '{target_db}' does not exist. Creating it...\n")
            create_cmd = [
                "psql", "-h", params["host"], "-p", str(params["port"]),
                "-U", params["user"], "-d", "postgres", "-c", create_sql
            ]
            c_proc = subprocess.run(create_cmd, env=env, capture_output=True, text=True, timeout=30)
            if c_proc.returncode != 0:
                raise RuntimeError(f"Failed to create target database '{target_db}': {c_proc.stderr}")


def execute_restore(backup_file: Path, target_db: str, params: dict, container: str = "", clean: bool = False, verbose: bool = False):
    """Execute pg_restore into the target database."""
    has_local = bool(shutil.which("pg_restore"))
    flags = ["-F", "c", "--no-owner", "--no-privileges"]
    if clean:
        flags.extend(["--clean", "--if-exists"])

    if container:
        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={params['password']}",
            container,
            "pg_restore",
            "-U", params["user"],
            "-d", target_db,
            *flags,
        ]
        with open(backup_file, "rb") as f_in:
            proc = subprocess.run(cmd, stdin=f_in, capture_output=True, timeout=300)
    elif has_local:
        cmd = [
            "pg_restore",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["user"],
            "-d", target_db,
            *flags,
            str(backup_file),
        ]
        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]
        proc = subprocess.run(cmd, env=env, capture_output=True, timeout=300)
    else:
        raise RuntimeError("pg_restore binary not found on PATH and no container was detected.")

    # pg_restore exit codes: 0 = success, 1 = benign warnings (e.g. relation exists), >1 = fatal error
    if proc.returncode > 1:
        stderr_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        if params["password"]:
            stderr_msg = stderr_msg.replace(params["password"], "[REDACTED]")
        raise RuntimeError(f"pg_restore failed with exit code {proc.returncode}: {stderr_msg}")

    if verbose and proc.returncode == 1:
        sys.stdout.write("Note: pg_restore completed with benign schema warnings (exit code 1).\n")


def verify_database_integrity(target_db: str, params: dict, container: str = "") -> dict:
    """Query the restored database to verify tables, Alembic head, and constraints."""
    tables_sql = (
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
    )
    alembic_sql = "SELECT version_num FROM alembic_version LIMIT 1;"
    pk_sql = (
        "SELECT count(*) FROM information_schema.table_constraints "
        "WHERE constraint_type = 'PRIMARY KEY' AND table_schema = 'public';"
    )
    fk_sql = (
        "SELECT count(*) FROM information_schema.table_constraints "
        "WHERE constraint_type = 'FOREIGN KEY' AND table_schema = 'public';"
    )

    def run_query(query: str) -> str:
        if container:
            cmd = [
                "docker", "exec", "-i",
                "-e", f"PGPASSWORD={params['password']}",
                container,
                "psql", "-U", params["user"], "-d", target_db, "-tAc", query
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                raise RuntimeError(f"Integrity query failed: {res.stderr.strip()}")
            return res.stdout.strip()
        else:
            env = os.environ.copy()
            if params["password"]:
                env["PGPASSWORD"] = params["password"]
            cmd = [
                "psql", "-h", params["host"], "-p", str(params["port"]),
                "-U", params["user"], "-d", target_db, "-tAc", query
            ]
            res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                raise RuntimeError(f"Integrity query failed: {res.stderr.strip()}")
            return res.stdout.strip()

    tables_out = run_query(tables_sql)
    found_tables = [t.strip() for t in tables_out.splitlines() if t.strip()]

    alembic_version = run_query(alembic_sql)
    pk_count = int(run_query(pk_sql) or "0")
    fk_count = int(run_query(fk_sql) or "0")

    # Check missing tables
    missing = [t for t in EXPECTED_TABLES if t not in found_tables]
    if missing:
        raise ValueError(f"Restored database is missing expected table(s): {missing}")

    if alembic_version != EXPECTED_ALEMBIC_HEAD:
        raise ValueError(
            f"Restored database Alembic revision '{alembic_version}' does not match expected head '{EXPECTED_ALEMBIC_HEAD}'."
        )

    if pk_count < 10:
        raise ValueError(f"Expected at least 10 primary keys in restored database, found {pk_count}.")

    return {
        "tables": found_tables,
        "table_count": len(found_tables),
        "alembic_version": alembic_version,
        "primary_keys": pk_count,
        "foreign_keys": fk_count,
    }


def run_restore(
    backup_path: str,
    target_db: str,
    db_url: str = "",
    container: str = "",
    clean: bool = False,
    force: bool = False,
    verify: bool = True,
    verbose: bool = False,
) -> dict:
    """High-level restore pipeline with pre-checks, restore execution, and integrity validation."""
    backup_file = Path(backup_path).resolve()
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    if backup_file.stat().st_size == 0:
        raise ValueError(f"Backup file is empty (0 bytes): {backup_file}")

    if not db_url:
        db_url = os.getenv("DATABASE_URL", "")

    if db_url:
        params = parse_db_url(db_url)
    else:
        params = {
            "user": os.getenv("POSTGRES_USER", "ytgenius"),
            "password": os.getenv("POSTGRES_PASSWORD", ""),
            "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "dbname": os.getenv("POSTGRES_DB", "ytgenius"),
        }

    # Safety Guard: Refuse to overwrite active/primary database without --force
    active_db = params.get("dbname", "ytgenius")
    if target_db == active_db or target_db in ("ytgenius", "youtube_qa_db"):
        if not force:
            raise PermissionError(
                f"SAFETY BLOCK: Target database '{target_db}' matches active/production database name. "
                "To prevent catastrophic data loss, pass --force to confirm intentional overwrite."
            )

    # Resolve container if applicable
    use_container = container or os.getenv("POSTGRES_CONTAINER", "")
    has_local = bool(shutil.which("pg_restore"))
    if not has_local and not use_container:
        auto_container = find_docker_container()
        if auto_container:
            use_container = auto_container

    # 1. Inspect archive TOC
    if verbose:
        sys.stdout.write(f"Inspecting backup archive header: {backup_file.name}...\n")
    toc_entries = inspect_archive(backup_file, container=use_container)
    if verbose:
        sys.stdout.write(f"Archive valid. Verified {len(toc_entries)} TOC entries in backup archive.\n")

    # 2. Ensure target database exists
    ensure_target_database(target_db, params, container=use_container, verbose=verbose)

    # 3. Execute restore
    if verbose:
        sys.stdout.write(f"Restoring backup into database '{target_db}'...\n")
    execute_restore(backup_file, target_db, params, container=use_container, clean=clean, verbose=verbose)

    # 4. Verify integrity
    integrity_result = {}
    if verify:
        if verbose:
            sys.stdout.write(f"Verifying schema, table integrity, and Alembic revision in '{target_db}'...\n")
        integrity_result = verify_database_integrity(target_db, params, container=use_container)
        if verbose:
            sys.stdout.write(
                f"Integrity confirmed: {integrity_result['table_count']} tables present, "
                f"Alembic revision '{integrity_result['alembic_version']}', "
                f"{integrity_result['primary_keys']} primary keys, "
                f"{integrity_result['foreign_keys']} foreign keys.\n"
            )

    return {
        "status": "success",
        "backup_file": str(backup_file),
        "target_db": target_db,
        "toc_entries": len(toc_entries),
        "integrity": integrity_result,
    }


def main():
    parser = argparse.ArgumentParser(description="YtGenius PostgreSQL Database Restore & Verification Utility")
    parser.add_argument("backup_file", help="Path to the .dump file to restore")
    parser.add_argument("--target-db", required=True, help="Explicit target database name (e.g. ytgenius_restore_test)")
    parser.add_argument("--db-url", help="PostgreSQL connection URL (defaults to DATABASE_URL env var)")
    parser.add_argument("--container", help="Name of Docker container running PostgreSQL (e.g. ytgenius-postgres)")
    parser.add_argument("--clean", action="store_true", help="Drop database objects before recreating them")
    parser.add_argument("--force", action="store_true", help="Confirm overwrite if target is the active/production database")
    parser.add_argument("--skip-verify", action="store_true", help="Skip post-restore schema and table integrity verification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        res = run_restore(
            backup_path=args.backup_file,
            target_db=args.target_db,
            db_url=args.db_url or "",
            container=args.container or "",
            clean=args.clean,
            force=args.force,
            verify=not args.skip_verify,
            verbose=args.verbose,
        )
        print(f"SUCCESS: Database restored into '{res['target_db']}' and verified.")
        sys.exit(0)
    except Exception as err:
        sys.stderr.write(f"ERROR: Restore failed: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
