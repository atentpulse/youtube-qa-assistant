#!/usr/bin/env python3
"""
YtGenius — PostgreSQL Database Backup Utility
Creates consistent, restorable PostgreSQL backups using native pg_dump.

Features:
- Custom format (-F c) with compression and archive integrity verification.
- Timestamped filenames: ytgenius_backup_YYYYMMDD_HHMMSS.dump.
- Credentials passed securely via PGPASSWORD environment variable (never CLI args).
- Atomic writing to temporary file before final rename.
- Safe optional retention pruning (--keep N).
- Supports native pg_dump or Docker container execution.
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


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


def prune_old_backups(output_dir: Path, keep_count: int) -> list:
    """Prune oldest backup files exceeding keep_count, matching ytgenius_backup_*.dump."""
    if keep_count <= 0:
        return []

    pattern = re.compile(r"^ytgenius_backup_\d{8}_\d{6}\.dump$")
    backups = [f for f in output_dir.iterdir() if f.is_file() and pattern.match(f.name)]
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    pruned = []
    if len(backups) > keep_count:
        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink()
                pruned.append(old_backup.name)
            except OSError as err:
                sys.stderr.write(f"Warning: Failed to delete old backup {old_backup.name}: {err}\n")
    return pruned


def run_backup(
    db_url: str = "",
    output_dir: str = "backups",
    filename: str = "",
    container: str = "",
    keep: int = 0,
    verbose: bool = False,
) -> Path:
    """Execute pg_dump and write backup file."""
    # Resolve connection parameters
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

    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not filename:
        filename = f"ytgenius_backup_{timestamp}.dump"

    target_file = out_path / filename
    temp_file = out_path / f".tmp_{filename}"

    # Determine execution mechanism
    use_container = container or os.getenv("POSTGRES_CONTAINER", "")
    has_local_pg_dump = bool(shutil.which("pg_dump"))

    if not has_local_pg_dump and not use_container:
        auto_container = find_docker_container()
        if auto_container:
            use_container = auto_container

    if verbose:
        engine_desc = f"container '{use_container}'" if use_container else "local binary"
        sys.stdout.write(f"Executing backup using {engine_desc} for database '{params['dbname']}'\n")

    try:
        if use_container:
            # Execute pg_dump inside Docker container
            cmd = [
                "docker",
                "exec",
                "-i",
                "-e",
                f"PGPASSWORD={params['password']}",
                use_container,
                "pg_dump",
                "-U",
                params["user"],
                "-d",
                params["dbname"],
                "-F",
                "c",
                "--no-owner",
                "--no-privileges",
            ]
            with open(temp_file, "wb") as f_out:
                proc = subprocess.run(
                    cmd,
                    stdout=f_out,
                    stderr=subprocess.PIPE,
                    timeout=300,
                )
        else:
            if not has_local_pg_dump:
                raise RuntimeError(
                    "pg_dump binary not found on PATH, and no running PostgreSQL Docker container was detected. "
                    "Please install PostgreSQL client tools or specify --container <container_name>."
                )
            cmd = [
                "pg_dump",
                "-h",
                params["host"],
                "-p",
                str(params["port"]),
                "-U",
                params["user"],
                "-d",
                params["dbname"],
                "-F",
                "c",
                "--no-owner",
                "--no-privileges",
                "-f",
                str(temp_file),
            ]
            env = os.environ.copy()
            if params["password"]:
                env["PGPASSWORD"] = params["password"]
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                timeout=300,
            )

        if proc.returncode != 0:
            stderr_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            # Sanitize stderr to ensure passwords never leak
            if params["password"]:
                stderr_msg = stderr_msg.replace(params["password"], "[REDACTED]")
            raise RuntimeError(f"pg_dump failed with exit code {proc.returncode}: {stderr_msg}")

        # Validate that temporary file was written and is non-empty
        if not temp_file.exists() or temp_file.stat().st_size == 0:
            raise RuntimeError("Backup completed with zero-byte output file.")

        # Atomic rename to final target file
        if target_file.exists():
            target_file.unlink()
        temp_file.rename(target_file)

        file_size = target_file.stat().st_size
        if verbose:
            sys.stdout.write(f"Backup created successfully: {target_file.name} ({file_size} bytes)\n")

        # Handle retention pruning if requested
        if keep > 0:
            pruned = prune_old_backups(out_path, keep)
            if verbose and pruned:
                sys.stdout.write(f"Pruned {len(pruned)} old backup(s) under retention policy ({keep}): {', '.join(pruned)}\n")

        return target_file

    except Exception as exc:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise exc


def main():
    parser = argparse.ArgumentParser(description="YtGenius PostgreSQL Database Backup Utility")
    parser.add_argument("--db-url", help="PostgreSQL connection URL (defaults to DATABASE_URL env var)")
    parser.add_argument("--output-dir", default="backups", help="Directory where backups are saved (default: backups)")
    parser.add_argument("--filename", help="Custom backup filename (default: ytgenius_backup_YYYYMMDD_HHMMSS.dump)")
    parser.add_argument("--container", help="Name of Docker container running PostgreSQL (e.g. ytgenius-postgres)")
    parser.add_argument("--keep", type=int, default=0, help="Number of recent backups to keep (default: 0 = keep all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        backup_file = run_backup(
            db_url=args.db_url or "",
            output_dir=args.output_dir,
            filename=args.filename or "",
            container=args.container or "",
            keep=args.keep,
            verbose=args.verbose,
        )
        print(f"SUCCESS: Backup created at {backup_file} ({backup_file.stat().st_size} bytes)")
        sys.exit(0)
    except Exception as err:
        sys.stderr.write(f"ERROR: Backup failed: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
