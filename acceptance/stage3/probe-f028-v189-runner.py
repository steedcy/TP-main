"""SRS_F028 V1.189 independent verification runner.
Orchestrates backend startup, proxy, protocol probe, and real Edge browser UI test.
"""
import copy, hashlib, json, mimetypes, os, socket, subprocess, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

ROOT = Path('C:/Users/savy/Desktop/TIP-main/tip-gpt-f013')
old = ROOT.parent / 'tip'
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
    print("=== 启动 SRS_F028 V1.189 整轮独立复测 Runner ===")

    # 1. 检查端口
    for p in [18129, 15179]:
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', p)) == 0:
                print(f"Error: 端口 {p} 已被占用，请先释放")
                sys.exit(1)
    print("1. 端口检查通过 (18129, 15179 空闲)")

    # 2. 启动生产打包的后端应用
    print("2. 启动后端应用 (V1.189 JAR)...")
    start_jar = ROOT / 'acceptance/stage3/fixtures/start-f028-v189-jar.py'
    ret = subprocess.run([sys.executable, str(start_jar)], cwd=ROOT)
    if ret.returncode != 0:
        print("Error: 后端启动失败")
        sys.exit(1)

    runtime_file = ROOT / '.local-test/runtime-v189.json'
    backend_pid = None
    if runtime_file.exists():
        backend_pid = json.loads(runtime_file.read_text(encoding='utf-8')).get('pid')
    print(f"后端启动成功 (PID: {backend_pid})")

    # 3. 启动前端代理服务 (15179)
    print("3. 启动前端代理服务 (端口: 15179)...")
    proxy_server = ThreadingHTTPServer(('127.0.0.1', 15179), ProxyHandler)
    t_proxy = threading.Thread(target=proxy_server.serve_forever, daemon=True)
    t_proxy.start()
    print("前端代理服务已启动")

    probe_passed = False
    ui_passed = False

    try:
        # 4. 执行协议层与数据库整轮独立测试
        print("\n4. 运行协议层与数据库独立测试 probe-f028-v189.py...")
        probe_py = ROOT / 'acceptance/stage3/probe-f028-v189.py'
        probe_ret = subprocess.run([sys.executable, str(probe_py)], cwd=ROOT)
        if probe_ret.returncode == 0:
            probe_passed = True
            print("协议层与数据库独立测试全部通过！")
        else:
            print("Error: 协议层测试失败，返回码:", probe_ret.returncode)

        # 5. 执行真实 Edge 浏览器 UI 自动化测试
        print("\n5. 运行真实 Edge 浏览器 UI 测试 retest-f028-v189-real-ui.cjs...")
        ui_script = ROOT / 'acceptance/stage3/retest-f028-v189-real-ui.cjs'
        ui_env = os.environ.copy()
        ui_ret = subprocess.run(['node', str(ui_script)], cwd=ROOT, env=ui_env, capture_output=True, encoding='utf-8', errors='replace')
        print("UI 测试标准输出:\n", ui_ret.stdout)
        if ui_ret.stderr:
            print("UI 测试标准错误:\n", ui_ret.stderr)

        ui_results_path = EVIDENCE / 'SRS_F028-V1.189-real-ui-results.json'
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
        time.sleep(1)

    print("\n================ 复测结论汇总 ================")
    print(f"协议与数据库独立测试 (SRS_F028.R01~R08, TC-085.S1~S2): {'[P] 全部通过' if probe_passed else '[F] 失败'}")
    print(f"DEF-S3-009 彻底关闭验证: {'[P] 通过 (before/after 摘要结构化且脱敏)' if probe_passed else '[F] 失败'}")
    print(f"真实 Edge 浏览器 UI 实测: {'[P] 全部通过' if ui_passed else '[F] 失败'}")
    overall = probe_passed and ui_passed
    print(f"整体验收裁决: {'REQUIREMENT_PASSED (ALL PASSED)' if overall else 'FAILED'}")
    print("=============================================")

    if not overall:
        sys.exit(1)

if __name__ == '__main__':
    main()
