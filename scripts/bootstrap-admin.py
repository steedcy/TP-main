#!/usr/bin/env python3
"""Set the initial admin password after Flyway has created its placeholder row."""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    for tool in ("mvn", "javac", "java", "psql"):
        if not any(
            pathlib.Path(directory, tool + suffix).is_file()
            for directory in os.environ.get("PATH", "").split(os.pathsep)
            for suffix in (".exe", ".cmd", ".bat", "")
        ):
            raise SystemExit(f"Required tool not found on PATH: {tool}")

    with tempfile.TemporaryDirectory(prefix="airport-ai-admin-") as temp:
        temp_path = pathlib.Path(temp)
        classpath_file = temp_path / "classpath.txt"
        subprocess.run(
            [
                "mvn",
                "-q",
                "-f",
                str(ROOT / "backend" / "pom.xml"),
                "dependency:build-classpath",
                f"-Dmdep.outputFile={classpath_file}",
            ],
            check=True,
        )
        dependency_classpath = classpath_file.read_text(encoding="utf-8").strip()
        subprocess.run(
            [
                "javac",
                "-cp",
                dependency_classpath,
                "-d",
                str(temp_path),
                str(ROOT / "scripts" / "PasswordHash.java"),
            ],
            check=True,
        )

        hash_file = temp_path / "admin.hash"
        subprocess.run(
            [
                "java",
                "-cp",
                os.pathsep.join((str(temp_path), dependency_classpath)),
                "PasswordHash",
                str(hash_file),
            ],
            check=True,
        )
        password_hash = hash_file.read_text(encoding="utf-8").strip()

    environment = os.environ.copy()
    environment["PGHOST"] = environment.get("DB_HOST", "localhost")
    environment["PGPORT"] = environment.get("DB_PORT", "5432")
    environment["PGDATABASE"] = environment.get("DB_NAME", "airport_ai")
    environment["PGUSER"] = environment.get("DB_USERNAME", "airportai_user")
    if "DB_PASSWORD" in environment:
        environment["PGPASSWORD"] = environment["DB_PASSWORD"]

    sql = (
        f"\\set admin_hash {password_hash}\n"
        "UPDATE users SET password_hash = :'admin_hash' "
        "WHERE username = 'admin' AND password_hash LIKE '%PLACEHOLDER%';\n"
    )
    result = subprocess.run(
        ["psql", "-X", "-w", "-v", "ON_ERROR_STOP=1", "-tA"],
        input=sql,
        text=True,
        env=environment,
        check=True,
        capture_output=True,
    )
    if result.stdout.strip() != "UPDATE 1":
        raise SystemExit(
            "No placeholder admin password was replaced. Check migration state and admin row; no account was overwritten."
        )
    print("Initial administrator password installed. Sign in as admin before exposing the service.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
