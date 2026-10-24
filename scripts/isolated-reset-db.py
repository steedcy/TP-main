"""Create and inspect a dedicated PostgreSQL schema for F2 reset verification.
Never points at the public application schema. Credentials stay in environment only.
"""
import importlib.util
import pathlib
import subprocess
import sys

spec = importlib.util.spec_from_file_location("localenv", pathlib.Path(__file__).with_name("local-test-environment.py"))
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)
variables = env.env()
psql = pathlib.Path(r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
isolated_schema = "tip_f2_reset_20261024"
shared = variables.get("DB_NAME", "airport_ai")
variables["PGPASSWORD"] = variables.get("DB_PASSWORD", "123456")
common = [str(psql), "-X", "-v", "ON_ERROR_STOP=1", "-h", variables.get("DB_HOST", "localhost"),
          "-p", variables.get("DB_PORT", "5432"), "-U", variables.get("DB_USERNAME", "admin")]

def sql(database, query):
    result = subprocess.run(common + ["-d", database, "-At", "-c", query], env=variables,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "psql failed")
    return result.stdout.strip()

if __name__ == "__main__":
    role = sql("postgres", "SELECT current_user")
    if len(sys.argv) > 1 and sys.argv[1] == "privileges":
        print("create schema privilege:", sql(shared,
              "SELECT has_database_privilege(current_user,current_database(),'CREATE')"))
    elif len(sys.argv) > 1 and sys.argv[1] == "create-schema":
        if isolated_schema == "public":
            raise SystemExit("refusing to use public schema")
        sql(shared, "CREATE SCHEMA IF NOT EXISTS " + isolated_schema)
        print("isolated schema ready:", isolated_schema, "in database:", shared)
    else:
        print("postgres connection ready; isolated schema:", isolated_schema, "role:", role)
