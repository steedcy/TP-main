<#
.SYNOPSIS
    在 Windows 本机预编译后端 JAR、仿真器 JAR 与前端静态资源，生成免服务器依赖下载的 CentOS 7 Docker 预编译部署包。
.EXAMPLE
    .\scripts\package-docker-prebuilt.ps1
    .\scripts\package-docker-prebuilt.ps1 -SkipBuild
#>
param(
    [switch]$SkipBuild,
    [string]$OutputArchive = "outputs\airport-ai-docker-prebuilt.tar.gz"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Staging = Join-Path $Root "outputs\docker-prebuilt-staging"
$ArchivePath = Join-Path $Root $OutputArchive

if (-not $SkipBuild) {
    Write-Host "[1/5] 编译后端应用 (airport-ai-app)..." -ForegroundColor Cyan
    & mvn -f (Join-Path $Root "backend\pom.xml") clean package -DskipTests
    if ($LASTEXITCODE -ne 0) { throw "后端编译失败" }

    Write-Host "[2/5] 编译设备仿真运行时 (device-simulator-runtime)..." -ForegroundColor Cyan
    & mvn -f (Join-Path $Root "simulator\pom.xml") clean package -DskipTests
    if ($LASTEXITCODE -ne 0) { throw "仿真器编译失败" }

    Write-Host "[3/5] 构建前端静态资源 (frontend/dist)..." -ForegroundColor Cyan
    & npm --prefix (Join-Path $Root "frontend") run build
    if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
}

$BackendJar = Join-Path $Root "backend\target\airport-ai-app-1.0.0.jar"
$SimulatorJar = Join-Path $Root "simulator\target\device-simulator-runtime.jar"
$FrontendDist = Join-Path $Root "frontend\dist"

if (-not (Test-Path $BackendJar)) { throw "未找到后端 JAR: $BackendJar" }
if (-not (Test-Path $SimulatorJar)) { throw "未找到仿真器 JAR: $SimulatorJar" }
if (-not (Test-Path (Join-Path $FrontendDist "index.html"))) { throw "未找到前端构建产物: $FrontendDist" }

Write-Host "[4/5] 组装预编译产物与引导工具 (prebuilt/)..." -ForegroundColor Cyan
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path `
    (Join-Path $Staging "prebuilt\bootstrap"), `
    (Join-Path $Staging "prebuilt\frontend-dist"), `
    (Join-Path $Staging "docker"), `
    (Join-Path $Staging "scripts"), `
    (Join-Path $Staging "docs") | Out-Null

Copy-Item $BackendJar (Join-Path $Staging "prebuilt\airport-ai-app.jar")
Copy-Item $SimulatorJar (Join-Path $Staging "prebuilt\device-simulator-runtime.jar")
Copy-Item (Join-Path $FrontendDist "*") (Join-Path $Staging "prebuilt\frontend-dist\") -Recurse

# 提取 spring-security-crypto / spring-jcl 并编译 PasswordHash.class 到 prebuilt/bootstrap
$BootstrapDir = Join-Path $Staging "prebuilt\bootstrap"
$JarExtractDir = Join-Path $Staging "prebuilt\_jar_tmp"
New-Item -ItemType Directory -Force -Path $JarExtractDir | Out-Null
Push-Location $JarExtractDir
try {
    & jar xf $BackendJar BOOT-INF/lib
    Get-ChildItem "BOOT-INF\lib" -Filter "spring-security-crypto-*.jar" | Copy-Item -Destination $BootstrapDir
    Get-ChildItem "BOOT-INF\lib" -Filter "spring-jcl-*.jar" | Copy-Item -Destination $BootstrapDir
    $Cp = ((Get-ChildItem $BootstrapDir -Filter "*.jar").FullName) -join ";"
    & javac -cp $Cp -d $BootstrapDir (Join-Path $Root "scripts\PasswordHash.java")
    if ($LASTEXITCODE -ne 0) { throw "PasswordHash.java 编译失败" }
} finally {
    Pop-Location
    Remove-Item $JarExtractDir -Recurse -Force -ErrorAction SilentlyContinue
}

Copy-Item (Join-Path $Root "docker-compose.yml") $Staging
Copy-Item (Join-Path $Root ".dockerignore") $Staging
Copy-Item (Join-Path $Root "docker\*") (Join-Path $Staging "docker\") -Recurse
Copy-Item (Join-Path $Root "scripts\*") (Join-Path $Staging "scripts\") -Recurse
Copy-Item (Join-Path $Root "docs\*.md") (Join-Path $Staging "docs\")

# 确保 Linux .sh 脚本全部为 LF 换行符
Get-ChildItem (Join-Path $Staging "scripts") -Filter "*.sh" | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes).Replace("`r`n", "`n")
    [System.IO.File]::WriteAllBytes($_.FullName, [System.Text.Encoding]::UTF8.GetBytes($text))
}

Write-Host "[5/5] 生成预编译部署压缩包 $OutputArchive ..." -ForegroundColor Cyan
$ArchiveDir = Split-Path -Parent $ArchivePath
if (-not (Test-Path $ArchiveDir)) { New-Item -ItemType Directory -Force -Path $ArchiveDir | Out-Null }
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }

$ArchiveItems = (Get-ChildItem -LiteralPath $Staging -Force | Select-Object -ExpandProperty Name)
& tar -czf $ArchivePath -C $Staging $ArchiveItems
if ($LASTEXITCODE -ne 0) { throw "tar 打包失败" }

Remove-Item $Staging -Recurse -Force

$Info = Get-Item $ArchivePath
$Hash = (Get-FileHash $ArchivePath -Algorithm SHA256).Hash
Write-Host "`n预编译打包完成: $($Info.FullName) ($($Info.Length) bytes)" -ForegroundColor Green
Write-Host "SHA-256: $Hash" -ForegroundColor Gray
Write-Host "`n上传至 CentOS 7 服务器 /tmp/ 后直接执行一键更新（免 Maven/npm 下载）：" -ForegroundColor Yellow
Write-Host "  scp $OutputArchive root@<服务器IP>:/tmp/"
Write-Host "  sudo bash /opt/airport-ai/repo/scripts/docker-update.sh --src /tmp/$(Split-Path -Leaf $OutputArchive)"
