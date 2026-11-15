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
    [switch]$TestRepo,
    # 只執行發布 staging 自我檢查（不建置 / 不 commit / 不 push / 不 tag）。
    # 供發布前驗證與隔離 index 測試使用。
    [switch]$StageOnly
)

$ErrorActionPreference = "Stop"

# ── 發布 staging 路徑分類 ────────────────────────────────────────
# 必要（Required）：發布流程專屬 / 版本核心。缺任一個 → 立即中止，不 commit / tag / push。
#   src/app.py、src/qt/version.py 等「應用程式原始碼」刻意不在此清單：
#   它們由 AGENTS.md 的分階段開發 commit 負責，release commit 只含發布流程專屬檔案。
$script:RequiredStagePaths = @(
    "src/_version.py",
    "latest_version.txt",
    "src/updater_core.py",
    "src/auto_update.py",
    "updater_main.py",
    "tools/build.py",
    "tools/make_delta.py",
    "scripts/requirements.txt",
    "release.ps1"
)

# 選擇性（Optional）：存在且未被 .gitignore 忽略才納入 staging。
#   不存在 → 只略過並提示（不得讓整個 staging 清單失敗）。
#   manifest.json / delta_info.json 為 .gitignore 排除的建置產物 → 一律略過（不使用 git add -f）。
$script:OptionalStagePaths = @(
    "latest_version_prerelease.txt",
    "pyproject.toml",
    "index.html",
    "sitemap.xml",
    "manifest.json",
    "delta_info.json"
)

function Invoke-Git {
    <#
      .SYNOPSIS
      執行 git 原生指令並嚴格檢查 exit code；失敗即中止發布流程。
      .DESCRIPTION
      $? 只反映 PowerShell cmdlet 成功與否，對原生指令無效 → 一律以 $LASTEXITCODE 判斷。
      原生指令的 stderr 在 ErrorActionPreference=Stop 下可能被視為錯誤，故函式內改用 Continue。
    #>
    param(
        [Parameter(Mandatory = $true)][string[]]$GitArgs,
        [Parameter(Mandatory = $true)][string]$Stage
    )
    Write-Host "  > git $($GitArgs -join ' ')"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    $code = 1
    try {
        & git @GitArgs 2>&1 | Out-Host
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($code -ne 0) {
        Write-Host "[ERROR] [$Stage] git $($GitArgs -join ' ') 失敗（exit $code）→ 已中止發布流程。" -ForegroundColor Red
        exit 1
    }
}

function Get-RepoDirtyPaths {
    <#
      .SYNOPSIS
      取得 repo 根目錄下所有未提交（含未追蹤）路徑，格式為 repo 根相對路徑。
    #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $lines = & git status --porcelain
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($code -ne 0) {
        Write-Host "[ERROR] git status 失敗（exit $code）→ 已中止發布流程。" -ForegroundColor Red
        exit 1
    }
    $paths = @()
    foreach ($line in @($lines)) {
        if (-not $line) { continue }
        $p = $line.Substring(3).Trim()
        if ($p -match '^(.+) -> (.+)$') { $p = $Matches[2] }
        $paths += $p.Trim('"')
    }
    return $paths
}

function Invoke-ReleaseStage {
    <#
      .SYNOPSIS
      依「必要 / 選擇性」分類 staging 發布檔案，並在每一步檢查 exit code。
    #>
    param([string]$RepoRoot = $PSScriptRoot)
    Push-Location $RepoRoot
    try {
        # ── 前置檢查：不得有未提交的開發修改 ──
        # release commit 只允許含發布流程專屬檔案；其餘未提交修改必須先依 AGENTS.md 提交，
        # 否則會被靜默遺漏（發布出去的 tag 原始碼與實際發布的 EXE 不一致）。
        $allowed = @($script:RequiredStagePaths) + @($script:OptionalStagePaths)
        $dirty = Get-RepoDirtyPaths -RepoRoot $RepoRoot
        $unexpected = @($dirty | Where-Object { $allowed -notcontains $_ })
        if ($unexpected.Count -gt 0) {
            Write-Host "[ERROR] 工作區仍有未提交的開發修改，發布 commit 只允許納入發布流程專屬檔案：" -ForegroundColor Red
            foreach ($p in $unexpected) { Write-Host "        - $p" -ForegroundColor Red }
            Write-Host "  請先依 AGENTS.md 規範分階段 commit 後再發布（release.ps1 不會代為提交開發修改）。" -ForegroundColor Yellow
            exit 1
        }

        # ── 必要路徑存在性：缺任一個即中止 ──
        $missing = @()
        foreach ($p in $script:RequiredStagePaths) {
            if (-not (Test-Path (Join-Path $RepoRoot $p))) { $missing += $p }
        }
        if ($missing.Count -gt 0) {
            Write-Host "[ERROR] 缺少必要的發布檔案，已中止（未 commit / tag / push）：" -ForegroundColor Red
            foreach ($p in $missing) { Write-Host "        - $p" -ForegroundColor Red }
            exit 1
        }

        # ── 選擇性路徑：存在且未被 .gitignore 忽略才納入 ──
        $stagePaths = @($script:RequiredStagePaths)
        foreach ($p in $script:OptionalStagePaths) {
            if (-not (Test-Path (Join-Path $RepoRoot $p))) {
                Write-Host "  略過（不存在）：$p" -ForegroundColor DarkGray
                continue
            }
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            & git check-ignore -q -- $p
            $ignoreCode = $LASTEXITCODE
            $ErrorActionPreference = $prevEap
            if ($ignoreCode -eq 0) {
                Write-Host "  略過（被 .gitignore 忽略，本腳本不使用 git add -f）：$p" -ForegroundColor DarkGray
                continue
            }
            if ($ignoreCode -ne 1) {
                Write-Host "[ERROR] git check-ignore 失敗（exit $ignoreCode）：$p" -ForegroundColor Red
                exit 1
            }
            $stagePaths += $p
        }

        Invoke-Git -GitArgs (@("add", "--") + $stagePaths) -Stage "staging"

        $staged = @(& git diff --cached --name-only)
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] git diff --cached 失敗（exit $LASTEXITCODE）" -ForegroundColor Red
            exit 1
        }
        Write-Host "  已暫存 $($staged.Count) 個檔案："
        foreach ($f in $staged) { Write-Host "        - $f" }
    } finally {
        Pop-Location
    }
}

function Invoke-ReleaseCommitAndPush {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseVersion,
        [bool]$IsPreview = $false,
        [string]$RepoRoot = $PSScriptRoot
    )
    Write-Host "`n[6/7] Committing and pushing..."
    Push-Location $RepoRoot
    try {
        Invoke-ReleaseStage -RepoRoot $RepoRoot
        $message = if ($IsPreview) { "chore: release v$ReleaseVersion (preview)" } else { "chore: release v$ReleaseVersion" }
        Invoke-Git -GitArgs @("commit", "-m", $message) -Stage "commit"
        Invoke-Git -GitArgs @("push", "origin", "master") -Stage "push master"
    } finally {
        Pop-Location
    }
}

function Invoke-ReleaseTagAndPush {
    param(
        [Parameter(Mandatory = $true)][string]$TagName,
        [string]$RepoRoot = $PSScriptRoot
    )
    Write-Host "`n[7/7] Creating GitHub release: $TagName"
    Push-Location $RepoRoot
    try {
        Invoke-Git -GitArgs @("tag", $TagName) -Stage "tag"
        Invoke-Git -GitArgs @("push", "origin", $TagName) -Stage "push tag"
    } finally {
        Pop-Location
    }
}


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

# StageOnly：只做 staging 自我檢查（不動版本、不建置、不 commit / push / tag）
if ($StageOnly) {
    Write-Host "`n[StageOnly] 僅執行發布 staging 自我檢查（不建置 / 不 commit / 不 push / 不 tag）"
    Invoke-ReleaseStage
    Write-Host "`n[StageOnly] staging 檢查完成" -ForegroundColor Cyan
    exit 0
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
Invoke-ReleaseCommitAndPush -ReleaseVersion $currentVersion -IsPreview ([bool]$Preview) -RepoRoot $PSScriptRoot

# ── Git tag + GitHub Release ─────────────────────────────
$tagName = "v$currentVersion"
Write-Host "`n[7/7] Creating GitHub release: $tagName"
Invoke-ReleaseTagAndPush -TagName $tagName -RepoRoot $PSScriptRoot

if ($Preview) {
    gh release create $tagName `
        --title "v$currentVersion (preview)" `
        --prerelease `
        --generate-notes `
        @("$fixedZip") @($vpkAssets)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] gh release create 失敗（exit $LASTEXITCODE）" -ForegroundColor Red
        exit 1
    }
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
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] gh release create 失敗（exit $LASTEXITCODE）" -ForegroundColor Red
            exit 1
        }
        Write-Host "  delta asset attached: GameTools_HealthMonitor-delta.zip"
    } else {
        gh release create $tagName `
            --title "v$currentVersion" `
            --generate-notes `
            --draft `
            @("$fixedZip") @($vpkAssets)
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] gh release create 失敗（exit $LASTEXITCODE）" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host " Release v$currentVersion published!" -ForegroundColor Green
    Write-Host " ZIP: GameTools_HealthMonitor.zip (legacy chain)" -ForegroundColor Green
    Write-Host " Velopack: Setup.exe + nupkg assets attached" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
