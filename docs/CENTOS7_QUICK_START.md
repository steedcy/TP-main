### 第 1 步：把 3 个脚本上传到测试服务器
只需要把本机这 3 个文件覆盖到测试服务器项目目录的 `scripts/` 下（如果测试机用 Git 拉代码，直接 `git pull` 即可；如果手动传，用 `scp` 或文件工具传这 3 个文件）：
- `scripts/start-all.sh`
- `scripts/manage-local-test.sh`
- `scripts/local-test-environment.py`

例如在本机执行（把 `user@测试机IP:/项目路径/tip` 换成你实际的）：
```bash
scp scripts/start-all.sh scripts/manage-local-test.sh scripts/local-test-environment.py user@测试机IP:/项目路径/tip/scripts/
```

### 第 2 步：登录测试服务器执行启动
```bash
cd /项目路径/tip
chmod +x scripts/start-all.sh scripts/manage-local-test.sh
./scripts/start-all.sh
```

- 如果测试服务器之前已经配好数据库、Redis 和环境变量，直接执行上面 3 行就会自动把 **后端 + 所有仿真体 + 前端** 全部拉起来。
- 只有当某一项启动报错（比如提示缺环境变量或缺少 `.jar`）时，再查看对应提示或 `.local-test/backend.log` 处理。
