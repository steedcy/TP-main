"""Run only the F2 reset integration test against the named isolated PostgreSQL schema."""
import importlib.util
import pathlib
import subprocess

spec = importlib.util.spec_from_file_location("isolated", pathlib.Path(__file__).with_name("isolated-reset-db.py"))
isolated = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolated)
schema = isolated.isolated_schema
assert schema == "tip_f2_reset_20261024" and schema != "public"
assert isolated.sql(isolated.shared,
       "SELECT count(*) FROM information_schema.schemata WHERE schema_name='" + schema + "'") == "1"
variables = isolated.variables.copy()
variables["DEMO_RESET_TEST_SCHEMA"] = schema
result = subprocess.run([r"C:\Program Files\apache-maven-3.10.0\bin\mvn.cmd", "-q", "-Dtest=DemoResetIntegrationTest", "test"],
                        cwd=isolated.env.ROOT / "backend", env=variables)
raise SystemExit(result.returncode)
