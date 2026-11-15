"""Supplement browser observations with local API authorization and audit evidence."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path('C:/Users/savy/Desktop/TIP-main/tip')
OUT = Path(__file__).parent / 'evidence/roles-e2e-20261115'
spec = importlib.util.spec_from_file_location('localenv', ROOT / 'scripts/local-test-environment.py')
env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(env)

def raw(path, method='GET', body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(env.BASE + path,
        json.dumps(body).encode() if body is not None else None, headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    apis = {role: env.API(role) for role in ['系统管理员', '配置管理员', '运行操作员']}
    checks = []
    for role, path in [('运行操作员', '/users'), ('配置管理员', '/users'),
                       ('配置管理员', '/tasks/273'), ('系统管理员', '/tasks/273')]:
        status, result = raw(path, token=apis[role].token)
        checks.append({'role': role, 'method': 'GET', 'path': path, 'httpStatus': status,
                       'code': result.get('code'), 'message': result.get('message')})
    admin = apis['系统管理员']
    username = 'e2e_roles_' + datetime.datetime.now().strftime('%H%M%S')
    password = secrets.token_urlsafe(15)
    status, created = raw('/users', 'POST', {'username': username, 'password': password,
        'realName': '三角色测试账号', 'role': 'OPERATOR', 'contact': 'roles-e2e@invalid.test'}, admin.token)
    lifecycle = [{'action': 'create', 'httpStatus': status, 'code': created.get('code')}]
    user_id = created.get('data', {}).get('id')
    if user_id:
        try:
            for state in ['INACTIVE', 'ACTIVE']:
                status, result = raw(f'/users/{user_id}/status', 'POST', {'status': state}, admin.token)
                lifecycle.append({'action': state, 'httpStatus': status, 'code': result.get('code')})
                status, login = raw('/auth/login', 'POST', {'username': username, 'password': password})
                lifecycle.append({'action': 'login_' + state, 'httpStatus': status,
                                  'code': login.get('code'), 'message': login.get('message')})
                if state == 'ACTIVE' and login.get('data', {}).get('token'):
                    session = login['data']['token']
                    status, result = raw('/auth/logout', 'POST', token=session)
                    lifecycle.append({'action': 'logout', 'httpStatus': status, 'code': result.get('code')})
                    status, result = raw('/tasks?page=1&size=1', token=session)
                    lifecycle.append({'action': 'reuse_logged_out_session', 'httpStatus': status,
                                      'code': result.get('code')})
        finally:
            status, result = raw(f'/users/{user_id}/status', 'POST', {'status': 'INACTIVE'}, admin.token)
            lifecycle.append({'action': 'final_disable', 'httpStatus': status, 'code': result.get('code')})
    save('api-security-account.json', {'time': env.stamp(), 'checks': checks,
        'testUsername': username, 'testUserId': user_id, 'lifecycle': lifecycle})
    runtime = ROOT / '.local-test/runtime/backend.jar'
    save('runtime.json', {'time': env.stamp(), 'backendSha256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
        'backendPath': str(runtime), 'frontend': 'http://localhost:5173', 'backend': env.BASE,
        'sourceHead': '58d586f135ed8234419ce51967e696984b653c3a', 'sourceDirty': True})
    source = Path('C:/Users/savy/Desktop/20260910-面向智慧机场的人工智能集群协同服务关键技术研究-需求规格说明书-V1.0.docx')
    with zipfile.ZipFile(source) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
    paragraphs = [''.join(p.itertext()) for p in document.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')]
    selected = [p for p in paragraphs if any(word in p for word in ['系统管理员', '配置管理员', '运行操作员', '超规行李', '特殊旅客', '航班变更'])]
    save('srs-source-check.json', {'fileName': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'paragraphCount': len(paragraphs), 'matchedParagraphCount': len(selected),
        'roleStatements': [p for p in selected if any(r in p for r in ['系统管理员', '配置管理员', '运行操作员'])][:18]})
    print(json.dumps({'accountLifecycle': lifecycle, 'authorization': checks}, ensure_ascii=False))

if __name__ == '__main__':
    main()
