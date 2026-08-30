# release.ps1
# 一鍵發佈腳本：版本號同步 → build → ZIP → git tag → GitHub Release
# Usage:
#   .\release.ps1                # 正式版：更新 latest_version.txt
#   .\release.ps1 -Preview       # 測試版：只更新 latest_version_prerelease.txt，建 Pre-release
#   .\release.ps1 -Version 1.3.0 # 指定版本號
#   .\release.ps1 -TestRepo [-Preview] [-Version X.Y.Z-test.N]
#                                # 測試倉模式：Velopack 資產只發到 release-test 倉，
#                                # 不碰主倉任何檔案/git/Release。用於發版前實測。
# Prerequisites: gh CLI (GitHub CLI) 已登入

param(
    [string]$Version = "",
    [switch]$Preview,
    [switch]$TestRepo
)

$ErrorActionPreference = "Stop"

# 測試倉（-TestRepo 模式的 Velopack 資產與 Release 目的地）
$testRepoSlug = "Sid-1996/PathofExile-Sid-GameTools_HealthMonitor_release-test"

# ── 讀取當前版本 ──────────────────────────────────────────
$versionFile = Join-Path $PSScriptRoot "src\_version.py"
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

# 版本檔同步（TestRepo 模式跳過：不碰主倉任何檔案）
$baseVersion = ""
if (-not $TestRepo) {
    # base_version = 上一版（覆寫 latest_version.txt 之前先讀，供 make_delta 比對）
    $latestFile = Join-Path $PSScriptRoot "latest_version.txt"
    if (Test-Path $latestFile) {
        $baseVersion = (Get-Content -Path $latestFile -Encoding utf8 | Select-Object -First 1).Trim()
    }
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
} else {
    Write-Host "  [TestRepo] skip version files / GitHub Pages sync"
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
if (-not $TestRepo) {
    Write-Host "`n[3/7] Cleaning old build artifacts..."
    $cleanupBat = Join-Path $PSScriptRoot "scripts\cleanup.bat"
    if (Test-Path $cleanupBat) { & $cleanupBat }
}

Write-Host "`n[4/7] Building EXE + updater.exe..."
$buildScript = Join-Path $PSScriptRoot "tools\build.py"
python $buildScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed" -ForegroundColor Red
    exit 1
}

$packageDir = Join-Path $PSScriptRoot "dist\GameTools_Package"
$vpkOut = Join-Path $PSScriptRoot "dist\vpk"

if (-not $TestRepo) {
    # ── 建立 release ZIP ──────────────────────────────────────
    Write-Host "`n[5/7] Preparing release ZIP..."
    $fixedZip = Join-Path $PSScriptRoot "dist\GameTools_HealthMonitor.zip"
    if (Test-Path $fixedZip) { Remove-Item $fixedZip -Force }
    Compress-Archive -Path "$packageDir\*" -DestinationPath $fixedZip
    Write-Host "  Created: GameTools_HealthMonitor.zip"

    # ── 差異更新（delta）── 僅 stable 發版產生（preview 會斷 delta 鏈）
    Write-Host "`n[5.5/7] Generating delta update..."
    if ($Preview) {
        Write-Host "  Preview: skip make_delta（delta 只對 stable 發佈）"
    } else {
        $makeDelta = Join-Path $PSScriptRoot "tools\make_delta.py"
        $packageDirForDelta = Join-Path $PSScriptRoot "dist\GameTools_Package"
        python $makeDelta $currentVersion $baseVersion $packageDirForDelta (Join-Path $PSScriptRoot "dist")
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] make_delta failed" -ForegroundColor Red
            exit 1
        }
    }
}

# ── Velopack 打包 ── 供 Setup.exe 安裝與自動更新（過渡期與舊 ZIP/delta 鏈並行）
# preview → --channel beta；stable → 預設 channel。
# 注意：delta nupkg 只會在同一 outputDir 有前一版 full nupkg 時產生；
#       主倉模式每次清空 outputDir → 無 delta（用戶端退回整包下載，可接受）；
#       TestRepo 模式保留 outputDir，連續兩輪不同版本即可實測 delta 差異更新。
Write-Host "`n[5.6/7] Building Velopack packages..."
if (-not $TestRepo) {
    if (Test-Path $vpkOut) { Remove-Item $vpkOut -Recurse -Force }
}
$vpkArgs = @(
    "pack",
    "--packId", "Sid.GameToolsHealthMonitor",
    "--packVersion", $currentVersion,
    "--packDir", $packageDir,
    "--mainExe", "GameTools_HealthMonitor.exe",
    "--outputDir", $vpkOut
)
if ($Preview) {
    $vpkArgs += @("--channel", "beta")
}
& vpk @vpkArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] vpk pack failed" -ForegroundColor Red
    exit 1
}
# 收集要上傳的 Velopack 資產：Setup.exe + *.nupkg + feed（portable.zip 不上傳——散佈模式為 installer）
# Velopack GithubSource 需要每個 Release 含 releases.*.json / RELEASES / assets.*.json 才會解析版本
$vpkAssets = @()
$vpkAssets += @(Get-ChildItem $vpkOut -Filter "*.nupkg" -ErrorAction SilentlyContinue | ForEach-Object FullName)
$vpkAssets += @(Get-ChildItem $vpkOut -Filter "*Setup.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName)
$vpkAssets += @(Get-ChildItem $vpkOut -Filter "releases.*.json" -ErrorAction SilentlyContinue | ForEach-Object FullName)
$vpkAssets += @((Join-Path $vpkOut "RELEASES") | Where-Object { Test-Path $_ })
$vpkAssets += @(Get-ChildItem $vpkOut -Filter "assets.*.json" -ErrorAction SilentlyContinue | ForEach-Object FullName)
$vpkAssets = @($vpkAssets | Sort-Object -Unique)
if ($vpkAssets.Count -eq 0) { Write-Host "[ERROR] No Velopack assets found in $vpkOut" -ForegroundColor Red; exit 1 }
Write-Host "  Velopack assets: $(($vpkAssets | ForEach-Object { Split-Path $_ -Leaf }) -join ', ')"

# ── TestRepo 模式：只把 Velopack 資產發到測試倉，完全不碰主倉 ──
if ($TestRepo) {
    $tagName = "v$currentVersion"
    Write-Host "`n[7/7] Creating test release on $testRepoSlug : $tagName"
    $relArgs = @(
        "release", "create", $tagName,
        "--repo", $testRepoSlug,
        "--title", $tagName
    )
    if ($Preview) {
        $relArgs += @("--prerelease", "--title", "$tagName (preview)")
    }
    gh @relArgs @($vpkAssets)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] gh release create (test repo) failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " TestRepo release v$currentVersion published!" -ForegroundColor Cyan
    if ($Preview) { Write-Host " Velopack channel: beta（client 需 allow_prerelease=true）" -ForegroundColor Cyan }
    else { Write-Host " Velopack channel: default" -ForegroundColor Cyan }
    if ($Version -and $Version -ne $currentVersion) {
        Write-Host " [提醒] _version.py 已被改為 $currentVersion，測試後請手動還原！" -ForegroundColor Yellow
    }
    Write-Host " client 端切換：寫 override 檔到 %LOCALAPPDATA%\GameTools_HealthMonitor\update_repo_override.txt" -ForegroundColor Cyan
    Write-Host " 內容：https://github.com/$testRepoSlug" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
}

# ── Git commit + push ────────────────────────────────────
Write-Host "`n[6/7] Committing and pushing..."
git add src/_version.py latest_version.txt latest_version_prerelease.txt src/updater_core.py src/auto_update.py src/qt/version.py src/app.py updater_main.py tools/build.py tools/make_delta.py scripts/requirements.txt release.ps1 index.html sitemap.xml manifest.json delta_info.json
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
        @("$fixedZip") @($vpkAssets)
    Write-Host "`n========================================" -ForegroundColor Yellow
    Write-Host " Preview v$currentVersion published!" -ForegroundColor Yellow
    Write-Host " latest_version.txt UNCHANGED — users not notified" -ForegroundColor Yellow
    Write-Host " Velopack channel: beta | assets attached" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
} else {
    $deltaZip = Join-Path $PSScriptRoot "dist\GameTools_HealthMonitor-delta.zip"
    if (Test-Path $deltaZip) {
        gh release create $tagName `
            --title "v$currentVersion" `
            --generate-notes `
            --draft `
            @("$fixedZip", "$deltaZip") @($vpkAssets)
        Write-Host "  delta asset attached: GameTools_HealthMonitor-delta.zip"
    } else {
        gh release create $tagName `
            --title "v$currentVersion" `
            --generate-notes `
            --draft `
            @("$fixedZip") @($vpkAssets)
    }
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host " Release v$currentVersion published!" -ForegroundColor Green
    Write-Host " ZIP: GameTools_HealthMonitor.zip (legacy chain)" -ForegroundColor Green
    Write-Host " Velopack: Setup.exe + nupkg assets attached" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
