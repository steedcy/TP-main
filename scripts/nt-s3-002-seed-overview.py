"""Seed an ISOLATED schema with the NT-S3-002 overview sample (9 task statuses, 5 exception types, dry-run decoys).

Never touches the shared/public schema. Credentials come from the environment only and are never printed:
  FIXTURE_DB_HOST/PORT (default localhost:5432), FIXTURE_DB_NAME, FIXTURE_DB_USER, FIXTURE_DB_PASSWORD,
  FIXTURE_DB_SCHEMA (required, not "public"; Flyway must already have created the tables there),
  FIXTURE_PSQL (path to psql; default: psql on PATH).
Usage: python scripts/nt-s3-002-seed-overview.py seed     # load sample and print expected overview values
       python scripts/nt-s3-002-seed-overview.py expected # print expected values computed by independent SQL
"""
import json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
E = os.environ.get
SEED = ROOT / "scripts" / "test-fixtures" / "nt-s3-002-overview-seed.sql"


def psql(sql=None, file=None):
    schema = E("FIXTURE_DB_SCHEMA", "")
    if not schema or schema.lower() == "public":
        raise SystemExit("FIXTURE_DB_SCHEMA must name a dedicated non-public schema")
    cmd = [E("FIXTURE_PSQL", "psql"), "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", E("FIXTURE_DB_HOST", "localhost"),
           "-p", E("FIXTURE_DB_PORT", "5432"), "-U", E("FIXTURE_DB_USER", ""), "-d", E("FIXTURE_DB_NAME", "airport_ai"),
           "-At", "-c", f"SET search_path TO {schema}"]
    cmd += ["-f", str(file)] if file else ["-c", sql]
    env = dict(os.environ, PGPASSWORD=E("FIXTURE_DB_PASSWORD", ""))
    r = subprocess.run(cmd, env=env, text=True, capture_output=True)
    if r.returncode:
        raise SystemExit("psql failed: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    return r.stdout.strip()


def expected():
    rows = psql("SELECT status, count(*) FROM tasks WHERE is_dry_run = FALSE GROUP BY status")
    counts = {l.split("|")[0]: int(l.split("|")[1]) for l in rows.splitlines() if l}
    one = lambda q: int(psql(q).splitlines()[-1])
    return {
        "statusCounts": counts,
        "taskInProgress": one("SELECT count(*) FROM tasks WHERE is_dry_run=FALSE AND status IN ('PENDING_ASSIGNMENT','DOWNGRADING','EXECUTING')"),
        "pendingManual": one("SELECT count(*) FROM tasks WHERE is_dry_run=FALSE AND status='PENDING_MANUAL'"),
        "unhandledExceptions": one("SELECT count(*) FROM task_exceptions e JOIN tasks t ON t.id=e.task_id WHERE t.is_dry_run=FALSE AND e.exception_status='PENDING'"),
        "replanningToday": one("SELECT count(*) FROM task_events ev JOIN tasks t ON t.id=ev.task_id WHERE t.is_dry_run=FALSE AND ev.event_type='REPLANNING_TRIGGERED' AND ev.occurred_at >= date_trunc('day', now())"),
        "replanningLast7Days": one("SELECT count(*) FROM task_events ev JOIN tasks t ON t.id=ev.task_id WHERE t.is_dry_run=FALSE AND ev.event_type='REPLANNING_TRIGGERED' AND ev.occurred_at >= date_trunc('day', now()) - interval '6 days'"),
        "dryRunDecoysPresent": one("SELECT count(*) FROM tasks WHERE is_dry_run=TRUE AND task_code LIKE 'NT002-D-%'"),
        "designedExpectation": "COMPLETED=6 (not 12); inProgress=3+4+5=12; pendingManual=8; unhandled=3; replanToday=2; last7Days=2",
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["seed"]:
        psql(file=SEED)
        print(json.dumps(expected(), ensure_ascii=False, indent=2))
    elif sys.argv[1:] == ["expected"]:
        print(json.dumps(expected(), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
