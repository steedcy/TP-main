"""Inspect or clone the local F2 database without printing credentials.

The clone is deliberately a separate database. Existing databases are never
overwritten; snapshots stay in the ignored .local-test directory.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("localenv", ROOT / "scripts/local-test-environment.py")
localenv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localenv)
env = localenv.env()
env["PGPASSWORD"] = env.get("DB_PASSWORD", "")
bin_dir = pathlib.Path(r"C:\Program Files\PostgreSQL\15\bin")
source = env.get("DB_NAME", "airport_ai")
target = "airport_ai_stage2_v14"
schema = "tip_stage2_v14"
common = ["-h", env.get("DB_HOST", "localhost"), "-p", env.get("DB_PORT", "5432"),
          "-U", env.get("DB_USERNAME", "admin")]


def run(binary, arguments, capture=True):
    completed = subprocess.run([str(bin_dir / binary), *common, *arguments], env=env,
                               capture_output=capture, text=capture, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise RuntimeError((completed.stderr or "database command failed").strip().splitlines()[-1])
    return completed.stdout.strip() if capture else ""


def query(database, statement):
    return run("psql.exe", ["-X", "-A", "-F", "|", "-t", "-v", "ON_ERROR_STOP=1",
                            "-d", database, "-c", statement])


def inspect(database):
    statements = [
        "SELECT current_database(),current_user,(SELECT rolcreatedb FROM pg_roles WHERE rolname=current_user)",
        "SELECT installed_rank,version,description,success FROM flyway_schema_history ORDER BY installed_rank",
        "SELECT status,count(*) FROM tasks GROUP BY status ORDER BY status",
        "SELECT COUNT(*) FROM users",
        "SELECT COUNT(*) FROM devices",
    ]
    return {"database": database, "identity": query(database, statements[0]),
            "flyway": query(database, statements[1]).splitlines(),
            "taskStates": query(database, statements[2]).splitlines(),
            "userCount": query(database, statements[3]),
            "deviceCount": query(database, statements[4])}


def clone():
    if source == target:
        raise RuntimeError("source and target databases must differ")
    exists = query("postgres", "SELECT 1 FROM pg_database WHERE datname='" + target + "'")
    if exists:
        raise RuntimeError("target database already exists; refusing to overwrite it")
    backup = ROOT / ".local-test" / "stage2-source-before-clone.dump"
    backup.parent.mkdir(exist_ok=True)
    if backup.exists():
        raise RuntimeError("snapshot already exists; refusing to overwrite it")
    run("pg_dump.exe", ["-Fc", "-f", str(backup), source])
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    run("createdb.exe", ["-T", "template0", target])
    run("pg_restore.exe", ["-d", target, "--no-owner", "--no-privileges", str(backup)])
    print(json.dumps({"source": inspect(source), "target": inspect(target),
                      "snapshot": str(backup), "snapshotSha256": digest}, ensure_ascii=False, indent=2))


def prepare_schema():
    if schema == "public":
        raise RuntimeError("isolated schema cannot be public")
    exists = query(source, "SELECT 1 FROM information_schema.schemata WHERE schema_name='" + schema + "'")
    if exists:
        raise RuntimeError("isolated schema already exists; refusing to overwrite it")
    backup = ROOT / ".local-test" / "stage2-public-before-schema.dump"
    if backup.exists():
        raise RuntimeError("snapshot already exists; refusing to overwrite it")
    run("pg_dump.exe", ["-Fc", "-n", "public", "-f", str(backup), source])
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    query(source, "CREATE SCHEMA " + schema)
    print(json.dumps({"source": inspect(source), "isolatedSchema": schema,
                      "snapshot": str(backup), "snapshotSha256": digest,
                      "restoreCommand": "pg_restore --clean --if-exists -d " + source + " " + str(backup)},
                     ensure_ascii=False, indent=2))


def inspect_schema():
    return {"database": source, "schema": schema,
            "flyway": query(source, "SELECT installed_rank,version,success FROM " + schema + ".flyway_schema_history ORDER BY installed_rank").splitlines(),
            "roles": query(source, "SELECT role,count(*) FROM " + schema + ".users GROUP BY role ORDER BY role").splitlines(),
            "taskStates": query(source, "SELECT status,count(*) FROM " + schema + ".tasks GROUP BY status ORDER BY status").splitlines(),
            "devices": query(source, "SELECT count(*) FROM " + schema + ".devices"),
            "templates": query(source, "SELECT template_status,count(*) FROM " + schema + ".baseline_templates GROUP BY template_status ORDER BY template_status").splitlines()}


def seed_roles():
    count = query(source, "SELECT count(*) FROM " + schema + ".users WHERE username IN ('admin','oprator','set')")
    if count != "1":
        raise RuntimeError("expected only the new placeholder admin in isolated schema")
    identities = query(source, "SELECT username,role,status FROM public.users WHERE username IN ('admin','oprator','set') ORDER BY username")
    if len(identities.splitlines()) != 3:
        raise RuntimeError("three source roles not present")
    statement = ("BEGIN; DELETE FROM " + schema + ".users WHERE username='admin'; "
                 "INSERT INTO " + schema + ".users SELECT * FROM public.users "
                 "WHERE username IN ('admin','oprator','set'); "
                 "SELECT setval(pg_get_serial_sequence('" + schema + ".users','id'), "
                 "(SELECT max(id) FROM " + schema + ".users)); COMMIT;")
    query(source, statement)
    print(json.dumps({"sourceRoles": identities.splitlines(), "isolated": inspect_schema()}, ensure_ascii=False, indent=2))


def snapshot_ready():
    backup = ROOT / ".local-test" / "stage2-ready-v14.dump"
    if backup.exists():
        raise RuntimeError("ready snapshot already exists; refusing to overwrite it")
    run("pg_dump.exe", ["-Fc", "-n", schema, "-f", str(backup), source])
    listing = run("pg_restore.exe", ["-l", str(backup)])
    if "flyway_schema_history" not in listing or "tasks" not in listing:
        raise RuntimeError("snapshot archive contents did not validate")
    print(json.dumps({"snapshot": str(backup), "snapshotSha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
                      "archiveEntries": len(listing.splitlines()), "state": inspect_schema()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "clone", "prepare-schema", "inspect-schema", "seed-roles", "snapshot-ready"])
    parser.add_argument("--database", default=source)
    args = parser.parse_args()
    if args.action == "inspect":
        print(json.dumps(inspect(args.database), ensure_ascii=False, indent=2))
    elif args.action == "clone":
        clone()
    elif args.action == "prepare-schema":
        prepare_schema()
    elif args.action == "inspect-schema":
        print(json.dumps(inspect_schema(), ensure_ascii=False, indent=2))
    elif args.action == "seed-roles":
        seed_roles()
    else:
        snapshot_ready()
