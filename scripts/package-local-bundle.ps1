<#
.SYNOPSIS
    在 Windows 本机完成前后端与仿真器的编译打包，并生成可上传至 Ubuntu 24.04.1 LTS 的一键部署压缩包。
.EXAMPLE
    .\scripts\package-local-bundle.ps1
    .\scripts\package-local-bundle.ps1 -SkipNpmInstall
#>
param(
    [switch]$SkipNpmInstall,
    [string]$OutputArchive = "outputs\airport-ai-ubuntu24-bundle.tar.gz"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Staging = Join-Path $Root "outputs\bundle-staging"
$ArchivePath = Join-Path $Root $OutputArchive

Write-Host "[1/5] 编译后端应用 (airport-ai-app)..." -ForegroundColor Cyan
& mvn -f (Join-Path $Root "backend\pom.xml") clean package -DskipTests
if ($LASTEXITCODE -ne 0) { throw "后端编译失败" }

Write-Host "[2/5] 编译设备仿真运行时 (device-simulator-runtime)..." -ForegroundColor Cyan
& mvn -f (Join-Path $Root "simulator\pom.xml") clean package -DskipTests
if ($LASTEXITCODE -ne 0) { throw "仿真器编译失败" }

Write-Host "[3/5] 构建前端静态资源 (frontend/dist)..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
try {
    if (-not $SkipNpmInstall -or -not (Test-Path "node_modules")) {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci 失败" }
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
} finally {
    Pop-Location
}

Write-Host "[4/5] 组装部署资源到临时目录..." -ForegroundColor Cyan
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path `
    (Join-Path $Staging "backend\target"), `
    (Join-Path $Staging "simulator\target"), `
    (Join-Path $Staging "frontend\dist"), `
    (Join-Path $Staging "scripts"), `
    (Join-Path $Staging "docs") | Out-Null

Copy-Item (Join-Path $Root "backend\target\airport-ai-app-1.0.0.jar") (Join-Path $Staging "backend\target\")
Copy-Item (Join-Path $Root "backend\pom.xml") (Join-Path $Staging "backend\")
Copy-Item (Join-Path $Root "simulator\target\device-simulator-runtime.jar") (Join-Path $Staging "simulator\target\")
Copy-Item (Join-Path $Root "frontend\dist\*") (Join-Path $Staging "frontend\dist\") -Recurse

Copy-Item (Join-Path $Root "scripts\deploy-ubuntu24.sh") (Join-Path $Staging "scripts\")
Copy-Item (Join-Path $Root "scripts\bootstrap-admin.py") (Join-Path $Staging "scripts\")
Copy-Item (Join-Path $Root "scripts\PasswordHash.java") (Join-Path $Staging "scripts\")
Copy-Item (Join-Path $Root "docs\Ubuntu24.04测试环境部署文档.md") (Join-Path $Staging "docs\")

Write-Host "[5/5] 生成压缩包 $OutputArchive ..." -ForegroundColor Cyan
$ArchiveDir = Split-Path -Parent $ArchivePath
if (-not (Test-Path $ArchiveDir)) { New-Item -ItemType Directory -Force -Path $ArchiveDir | Out-Null }
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }

& tar -czf $ArchivePath -C $Staging .
if ($LASTEXITCODE -ne 0) { throw "tar 打包失败" }

Remove-Item $Staging -Recurse -Force

Write-Host "`n打包完成: $ArchivePath" -ForegroundColor Green
Write-Host "上传到 Ubuntu 24.04.1 LTS 服务器后执行：" -ForegroundColor Yellow
Write-Host "  mkdir -p /opt/airport-ai/repo && tar -xzf airport-ai-ubuntu24-bundle.tar.gz -C /opt/airport-ai/repo"
Write-Host "  cd /opt/airport-ai/repo && sudo bash scripts/deploy-ubuntu24.sh --skip-build --server-ip <服务器IP>"
