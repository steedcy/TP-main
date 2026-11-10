"""SRS_NF003 V1.191 independent verification runner.
Orchestrates mock model (port 18117), backend startup (port 18129), frontend proxy (port 15179),
protocol probe, and real Edge browser UI test.
"""
import copy, hashlib, json, mimetypes, os, socket, subprocess, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

ROOT = Path('C:/Users/savy/Desktop/TIP-main/tip-gpt-f013')
EVIDENCE = ROOT / 'acceptance/stage3/evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def handle_all(self):
        if self.path.startswith('/api/'):
            content_len = int(self.headers.get('Content-Length', '0'))
            payload = self.rfile.read(content_len) if content_len > 0 else None
            req = urllib.request.Request(
                'http://127.0.0.1:18129' + self.path,
                payload,
                {k: v for k, v in self.headers.items() if k.lower() in ['authorization', 'content-type']},
                method=self.command
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as res:
                    status = res.status
                    ctype = res.headers.get('Content-Type', 'application/json')
                    body = res.read()
            except urllib.error.HTTPError as ex:
                status = ex.code
                ctype = ex.headers.get('Content-Type', 'application/json')
                body = ex.read()
            except Exception as ex:
                status = 502
                body = json.dumps({'error': str(ex)}).encode('utf-8')
        else:
            p = self.path.split('?')[0].lstrip('/')
            f = ROOT / 'frontend/dist' / p
            if f.is_dir() or not f.exists():
                f = ROOT / 'frontend/dist/index.html'
            if f.exists():
                status = 200
                ctype = mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
                body = f.read_bytes()
            else:
                status = 404
                body = b'Not found'
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self): self.handle_all()
    def do_POST(self): self.handle_all()
    def do_PUT(self): self.handle_all()
    def do_DELETE(self): self.handle_all()

def main():
    print("=== 启动 SRS_NF003 V1.191 整轮独立复测 Runner ===")

    # 1. 检查并清理端口
    for p in [18117, 18129, 15179]:
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) == 0:
                print(f"Warning: 端口 {p} 已被占用，尝试查找并释放...")
                netstat_out = subprocess.run(f'netstat -ano | findstr :{p}', shell=True, capture_output=True, text=True).stdout
                for line in netstat_out.splitlines():
                    if 'LISTENING' in line:
                        pid = line.strip().split()[-1]
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                time.sleep(1)

    print("1. 端口检查通过 (18117, 18129, 15179 空闲)")

    # 2. 启动受控外部模型 Mock (18117)
    print("2. 启动受控外部模型 Mock (端口: 18117)...")
    model_script = ROOT / 'acceptance/stage3/fixtures/nf003-controlled-model.py'
    p_model = subprocess.Popen([sys.executable, str(model_script)], cwd=ROOT)
    time.sleep(1)
    print(f"受控模型已启动 (PID: {p_model.pid})")

    # 确保 DB 中有在线可用设备代理
    import importlib.util
    spec = importlib.util.spec_from_file_location('db', ROOT.parent / 'tip/scripts/isolated-reset-db.py')
    db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db)
    sc = 'tip_gpt_f006_v118_20261030'
    db.sql(db.shared, f"UPDATE {sc}.device_agents SET online_status='ONLINE', work_status='IDLE', last_reported_at=NOW() WHERE agent_code='AGT-D68FD3AB'")
    print("已确保 AGT-D68FD3AB 状态为 ONLINE")

    # 3. 启动后端应用 (V1.191 JAR, 端口 18129)
    print("3. 启动后端应用 (V1.191 JAR)...")
    start_jar = ROOT / 'acceptance/stage3/fixtures/start-nf003-v191-jar.py'
    ret = subprocess.run([sys.executable, str(start_jar)], cwd=ROOT)
    if ret.returncode != 0:
        print("Error: 后端启动失败")
        p_model.kill()
        sys.exit(1)

    runtime_file = ROOT / '.local-test/runtime-nf003-v191.json'
    backend_pid = None
    if runtime_file.exists():
        backend_pid = json.loads(runtime_file.read_text(encoding='utf-8')).get('pid')
    print(f"后端启动成功 (PID: {backend_pid})")

    # 4. 启动前端代理服务 (15179)
    print("4. 启动前端代理服务 (端口: 15179)...")
    proxy_server = ThreadingHTTPServer(('127.0.0.1', 15179), ProxyHandler)
    t_proxy = threading.Thread(target=proxy_server.serve_forever, daemon=True)
    t_proxy.start()
    print("前端代理服务已启动")

    probe_passed = False
    ui_passed = False

    try:
        # 5. 执行协议层与数据库整轮独立测试
        print("\n5. 运行协议层与数据库独立测试 probe-nf003-v191.py...")
        probe_py = ROOT / 'acceptance/stage3/probe-nf003-v191.py'
        probe_ret = subprocess.run([sys.executable, str(probe_py)], cwd=ROOT)
        if probe_ret.returncode == 0:
            probe_passed = True
            print("协议层与数据库独立测试全部通过！")
        else:
            print("Error: 协议层测试失败，返回码:", probe_ret.returncode)

        # 6. 执行真实 Edge 浏览器 UI 自动化测试
        print("\n6. 运行真实 Edge 浏览器 UI 测试 retest-nf003-v191-real-ui.cjs...")
        db.sql(db.shared, f"UPDATE {sc}.device_agents SET online_status='ONLINE', work_status='IDLE', last_reported_at=NOW() WHERE agent_code='AGT-D68FD3AB'")
        ui_script = ROOT / 'acceptance/stage3/retest-nf003-v191-real-ui.cjs'
        ui_env = os.environ.copy()
        ui_ret = subprocess.run(['node', str(ui_script)], cwd=ROOT, env=ui_env, capture_output=True, encoding='utf-8', errors='replace')
        print("UI 测试标准输出:\n", ui_ret.stdout)
        if ui_ret.stderr:
            print("UI 测试标准错误:\n", ui_ret.stderr)

        ui_results_path = EVIDENCE / 'SRS_NF003-V1.191-real-ui-results.json'
        if ui_results_path.exists():
            ui_results = json.loads(ui_results_path.read_text(encoding='utf-8'))
            tests = ui_results.get('tests', [])
            all_ui_passed = all(t.get('status') == 'PASSED' for t in tests)
            if all_ui_passed and len(tests) >= 3:
                ui_passed = True
                print(f"真实 Edge UI 测试全部通过 ({len(tests)}/{len(tests)})！")
            else:
                print(f"UI 测试存在未通过项: {tests}")
        else:
            print("Error: 未找到 UI 测试结果文件")

    finally:
        print("\n=== 环境清理与资源释放 ===")
        proxy_server.shutdown()
        if backend_pid:
            print(f"关闭后端进程 PID {backend_pid}...")
            subprocess.run(['taskkill', '/F', '/PID', str(backend_pid)], capture_output=True)
        if p_model:
            print(f"关闭受控模型 PID {p_model.pid}...")
            p_model.kill()
        try:
            db.sql(db.shared, f"UPDATE {sc}.device_agents SET online_status='OFFLINE', work_status='IDLE' WHERE agent_code='AGT-D68FD3AB'")
            print("已恢复 AGT-D68FD3AB 状态为 OFFLINE")
        except Exception:
            pass
        time.sleep(1)

    print("\n================ 复测结论汇总 ================")
    print(f"协议与数据库独立测试 (SRS_NF003.R01, TC-031.S2, TC-077, TC-086): {'[P] 全部通过' if probe_passed else '[F] 失败'}")
    print(f"DEF-S3-032 彻底关闭验证: {'[P] 通过 (顶层与多层嵌套/事件/澄清/落库零泄露)' if probe_passed else '[F] 失败'}")
    print(f"合法业务代号放行 (零误拒): {'[P] 通过 (CA1234/BAG-123456/区域代号正常放行)' if probe_passed else '[F] 失败'}")
    print(f"真实 Edge 浏览器 UI 实测: {'[P] 全部通过' if ui_passed else '[F] 失败'}")
    overall = probe_passed and ui_passed
    print(f"整体验收裁决: {'REQUIREMENT_PASSED (ALL PASSED)' if overall else 'FAILED'}")
    print("=============================================")

    if not overall:
        sys.exit(1)

if __name__ == '__main__':
    main()
