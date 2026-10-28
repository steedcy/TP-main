"""Isolated fault-injection fixture for NT-S3-001 / TC-002.S4 (login under auth-service / database failure).

Nothing here stops, restarts or reconfigures the shared PostgreSQL, the ChatGPT backend, or ports
8080/5173/8091-8096. The backend under test runs on its own port and reaches PostgreSQL ONLY through a
local TCP proxy owned by this script; the "database outage" is the proxy being closed, and "recovery"
is the proxy being reopened. The auth-service fault is covered by LoginFaultResponseTest (JUnit).

Required environment (never printed, never committed):
  FIXTURE_DB_UPSTREAM_HOST/PORT   PostgreSQL to forward to (default localhost:5432)
  FIXTURE_DB_NAME/USER/PASSWORD   an isolated database or schema owner you may write to
  FIXTURE_DB_SCHEMA               dedicated schema, e.g. tip_claude_f001 (never "public")
  FIXTURE_LOGIN_USER/PASSWORD     a valid ACTIVE account that exists in that schema
Optional: FIXTURE_BACKEND_PORT (default 18101), FIXTURE_PROXY_PORT (default 15501),
          FIXTURE_REDIS_DB (default 13), FIXTURE_EVIDENCE (output json path).
Usage: python scripts/nt-s3-001-fault-fixture.py run
"""
import json, os, pathlib, socket, subprocess, sys, threading, time, datetime
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
E = os.environ.get
BACKEND_PORT = int(E("FIXTURE_BACKEND_PORT", "18101"))
PROXY_PORT = int(E("FIXTURE_PROXY_PORT", "15501"))
FORBIDDEN_PORTS = {8080, 5173, *range(8091, 8097)}


class Proxy:
    def __init__(self, host, port, listen):
        self.target, self.listen, self.srv, self.conns, self.run = (host, port), listen, None, [], False

    def start(self):
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", self.listen))
        self.srv.listen(64)
        self.run = True
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while self.run:
            try:
                c, _ = self.srv.accept()
                u = socket.create_connection(self.target, timeout=5)
            except OSError:
                break
            self.conns += [c, u]
            for a, b in ((c, u), (u, c)):
                threading.Thread(target=self._pipe, args=(a, b), daemon=True).start()

    @staticmethod
    def _pipe(a, b):
        try:
            while (d := a.recv(65536)):
                b.sendall(d)
        except OSError:
            pass
        for s in (a, b):
            try: s.close()
            except OSError: pass

    def stop(self):  # simulate outage: refuse new and drop existing connections
        self.run = False
        for s in [self.srv, *self.conns]:
            try: s.close()
            except OSError: pass
        self.conns = []


def kill_tree(proc):
    """mvn spawns a child JVM that holds the port; terminate() alone leaves it running."""
    if proc.poll() is not None and os.name != "nt":
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        try: os.killpg(proc.pid, signal.SIGTERM)
        except OSError: pass
    try: proc.wait(timeout=20)
    except subprocess.TimeoutExpired: pass


def port_free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def post_login(user, password):
    body = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/auth/login", body,
                                 {"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def session_created(payload):
    return bool((payload.get("data") or {}).get("token"))


def wait_up(timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/actuator/health", timeout=3)
            return True
        except urllib.error.HTTPError:
            return True
        except OSError:
            time.sleep(2)
    return False


def run():
    assert BACKEND_PORT not in FORBIDDEN_PORTS and PROXY_PORT not in FORBIDDEN_PORTS, "port reserved by ChatGPT side"
    schema = E("FIXTURE_DB_SCHEMA", "")
    if not schema or schema == "public":
        raise SystemExit("FIXTURE_DB_SCHEMA must name a dedicated non-public schema")
    user, password = E("FIXTURE_LOGIN_USER"), E("FIXTURE_LOGIN_PASSWORD")
    if not (user and password):
        raise SystemExit("FIXTURE_LOGIN_USER / FIXTURE_LOGIN_PASSWORD required")
    proxy = Proxy(E("FIXTURE_DB_UPSTREAM_HOST", "localhost"), int(E("FIXTURE_DB_UPSTREAM_PORT", "5432")), PROXY_PORT)
    proxy.start()
    env = dict(os.environ,
               DB_HOST="127.0.0.1", DB_PORT=str(PROXY_PORT), DB_NAME=E("FIXTURE_DB_NAME", "airport_ai"),
               DB_USERNAME=E("FIXTURE_DB_USER", ""), DB_PASSWORD=E("FIXTURE_DB_PASSWORD", ""),
               SPRING_DATASOURCE_URL=f"jdbc:postgresql://127.0.0.1:{PROXY_PORT}/{E('FIXTURE_DB_NAME', 'airport_ai')}"
                                     f"?currentSchema={schema}",
               SPRING_FLYWAY_SCHEMAS=schema, SERVER_PORT=str(BACKEND_PORT),
               SPRING_DATASOURCE_HIKARI_CONNECTION_TIMEOUT="3000",
               SPRING_DATA_REDIS_DATABASE=E("FIXTURE_REDIS_DB", "13"))
    backend = subprocess.Popen(["mvn", "-o", "-q", "spring-boot:run"], cwd=ROOT / "backend", env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=(os.name == "nt"),
                               start_new_session=(os.name != "nt"))
    evidence = {"observedAt": datetime.datetime.now().astimezone().isoformat(), "step": "TC-002.S4",
                "backendPort": BACKEND_PORT, "proxyPort": PROXY_PORT, "schema": schema, "checks": {}}
    try:
        if not wait_up():
            raise SystemExit("isolated backend did not start")
        st, p = post_login(user, password)
        evidence["checks"]["baselineLogin"] = {"httpStatus": st, "sessionCreated": session_created(p)}
        proxy.stop()  # inject: database unreachable
        time.sleep(1)
        st, p = post_login(user, password)
        evidence["checks"]["databaseDown"] = {"httpStatus": st, "message": p.get("message"),
                                              "sessionCreated": session_created(p),
                                              "pass": p.get("message") == "系统繁忙，请稍后重试" and not session_created(p)}
        proxy.start()  # recover
        time.sleep(5)
        st, p = post_login(user, password)
        evidence["checks"]["afterRecovery"] = {"httpStatus": st, "sessionCreated": session_created(p),
                                               "pass": st == 200 and session_created(p)}
    finally:
        proxy.stop()
        kill_tree(backend)
        time.sleep(1)
        evidence["cleanup"] = {"backendPortFreed": port_free(BACKEND_PORT), "proxyPortFreed": port_free(PROXY_PORT)}
    out = pathlib.Path(E("FIXTURE_EVIDENCE", ROOT / ".local-test" / "nt-s3-001-fixture-result.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print("result written to", out)


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    else:
        print(__doc__)
