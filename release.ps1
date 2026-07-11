# release.ps1
# 一鍵發佈腳本：版本號同步 → build → ZIP → git tag → GitHub Release
# Usage:
#   .\release.ps1                # 正式版：更新 latest_version.txt
#   .\release.ps1 -Preview       # 測試版：只更新 latest_version_prerelease.txt，建 Pre-release
#   .\release.ps1 -Version 1.3.0 # 指定版本號
# Prerequisites: gh CLI (GitHub CLI) 已登入

param(
    [string]$Version = "",
    [switch]$Preview
)

$ErrorActionPreference = "Stop"

# ── 讀取當前版本 ──────────────────────────────────────────
$versionFile = Join-Path $PSScriptRoot "src" "_version.py"
$content = Get-Content $versionFile -Raw
if ($content -match '__version__\s*=\s*"(.+?)"') {
    $currentVersion = $Matches[1]
} else {
    Write-Host "[ERROR] Cannot read version from _version.py" -ForegroundColor Red
    exit 1
}

# 若有指定版本，更新 _version.py
if ($Version -and $Version -ne $currentVersion) {
    Write-Host "[1/7] Updating version: $currentVersion → $Version"
    $newContent = $content -replace "__version__\s*=\s*`"$currentVersion`"", "__version__ = `"$Version`""
    Set-Content $versionFile $newContent -Encoding UTF8
    $currentVersion = $Version
} else {
    Write-Host "[1/7] Using current version: $currentVersion"
}

# 版本檔同步
if ($Preview) {
    $preFile = Join-Path $PSScriptRoot "latest_version_prerelease.txt"
    Set-Content $preFile "$currentVersion`n" -Encoding UTF8
    Write-Host "  latest_version_prerelease.txt → $currentVersion (preview)"
    Write-Host "  latest_version.txt unchanged"
} else {
    Set-Content (Join-Path $PSScriptRoot "latest_version.txt") "$currentVersion`n" -Encoding UTF8
    Write-Host "  latest_version.txt → $currentVersion"
}

# ── 同步 GitHub Pages (index.html + sitemap.xml) ─────────
$indexHtml = Join-Path $PSScriptRoot "index.html"
if (Test-Path $indexHtml) {
    $htmlContent = Get-Content $indexHtml -Raw -Encoding UTF8
    $htmlContent = $htmlContent -replace '最新版本 <strong>v[^<]+</strong>', "最新版本 <strong>v$currentVersion</strong>"
    Set-Content $indexHtml $htmlContent -Encoding UTF8 -NoNewline
    Write-Host "  index.html → v$currentVersion"
}

$sitemapXml = Join-Path $PSScriptRoot "sitemap.xml"
if (Test-Path $sitemapXml) {
    $today = Get-Date -Format "yyyy-MM-dd"
    $sitemapContent = Get-Content $sitemapXml -Raw -Encoding UTF8
    $sitemapContent = $sitemapContent -replace '<lastmod>[^<]+</lastmod>', "<lastmod>$today</lastmod>"
    Set-Content $sitemapXml $sitemapContent -Encoding UTF8 -NoNewline
    Write-Host "  sitemap.xml → lastmod $today"
}

# ── 檢查 gh CLI ──────────────────────────────────────────
Write-Host "`n[2/7] Checking gh CLI..."
try {
    $ghUser = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Not logged in" }
    Write-Host "  gh CLI authenticated"
} catch {
    Write-Host "[ERROR] gh CLI not found or not logged in. Install: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

# ── 清理 + build ─────────────────────────────────────────
Write-Host "`n[3/7] Cleaning old build artifacts..."
$cleanupBat = Join-Path $PSScriptRoot "scripts" "cleanup.bat"
if (Test-Path $cleanupBat) { & $cleanupBat }

Write-Host "`n[4/7] Building EXE + updater.exe..."
$buildScript = Join-Path $PSScriptRoot "tools" "build.py"
python $buildScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed" -ForegroundColor Red
    exit 1
}

# ── 建立 release ZIP ──────────────────────────────────────
Write-Host "`n[5/7] Preparing release ZIP..."
$packageDir = Join-Path $PSScriptRoot "dist" "GameTools_Package"
$fixedZip = Join-Path $PSScriptRoot "dist" "GameTools_HealthMonitor.zip"
if (Test-Path $fixedZip) { Remove-Item $fixedZip -Force }
Compress-Archive -Path "$packageDir\*" -DestinationPath $fixedZip
Write-Host "  Created: GameTools_HealthMonitor.zip"

# ── Git commit + push ────────────────────────────────────
Write-Host "`n[6/7] Committing and pushing..."
git add src/_version.py latest_version.txt latest_version_prerelease.txt src/tab_version.py src/updater_core.py updater_main.py tools/build.py release.ps1 index.html sitemap.xml
if ($Preview) {
    git commit -m "chore: release v$currentVersion (preview)"
} else {
    git commit -m "chore: release v$currentVersion"
}
git push origin master

# ── Git tag + GitHub Release ─────────────────────────────
$tagName = "v$currentVersion"
Write-Host "`n[7/7] Creating GitHub release: $tagName"
git tag $tagName
git push origin $tagName

if ($Preview) {
    gh release create $tagName `
        --title "v$currentVersion (preview)" `
        --prerelease `
        --generate-notes `
        "$fixedZip"
    Write-Host "`n========================================" -ForegroundColor Yellow
    Write-Host " Preview v$currentVersion published!" -ForegroundColor Yellow
    Write-Host " latest_version.txt UNCHANGED — users not notified" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
} else {
    gh release create $tagName `
        --title "v$currentVersion" `
        --generate-notes `
        "$fixedZip"
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host " Release v$currentVersion published!" -ForegroundColor Green
    Write-Host " ZIP: GameTools_HealthMonitor.zip" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
