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
    "release.ps1",
    # 版本衍生欄位：pyproject.toml 會隨版本更新而變動，必須納入 release commit，
    # 否則工作區會殘留未提交的版本漂移。
    "pyproject.toml",
    # uv.lock 受版本控制：依賴鎖定檔必須跟著 release commit 一起走，
    # 否則 tag 上的原始碼與實際發布用的依賴組合不一致。
    "uv.lock"
)

# 選擇性（Optional）：存在且未被 .gitignore 忽略才納入 staging。
#   不存在 → 只略過並提示（不得讓整個 staging 清單失敗）。
#   manifest.json / delta_info.json 為 .gitignore 排除的建置產物 → 一律略過（不使用 git add -f）。
$script:OptionalStagePaths = @(
    "latest_version_prerelease.txt",
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

function Resolve-VenvPython {
    <#
      .SYNOPSIS
      取得專案鎖定的 .venv Python 路徑；.venv 不存在時明確失敗（絕不退回系統 Python）。
    #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "[ERROR] 找不到專案虛擬環境 Python：$venvPython" -ForegroundColor Red
        Write-Host "        請先建立環境：uv sync --locked（或 scripts\install_dependencies.bat）" -ForegroundColor Red
        exit 1
    }
    return $venvPython
}

function Test-VenvPythonModule {
    <#
      .SYNOPSIS
      檢查指定 Python 能否 import 某個模組（只回傳布林值，不中止流程）。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Module
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    $code = 1
    try {
        & $Python -c "import $Module" 2>&1 | Out-Null
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    return ($code -eq 0)
}

function Assert-VenvPythonModules {
    <#
      .SYNOPSIS
      確認指定 Python 可 import 所有必要模組；缺少時列出清單並以非零 exit code 中止。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [string[]]$RequiredModules = @()
    )
    $missing = @()
    foreach ($m in $RequiredModules) {
        if (-not (Test-VenvPythonModule -Python $Python -Module $m)) { $missing += $m }
    }
    if ($missing.Count -gt 0) {
        Write-Host "[ERROR] 專案 .venv 缺少必要套件：$($missing -join ', ')" -ForegroundColor Red
        Write-Host "        請執行：uv sync --locked（或 scripts\install_dependencies.bat）後再試" -ForegroundColor Red
        exit 1
    }
}

function Resolve-BuildPython {
    <#
      .SYNOPSIS
      取得正式建置要使用的 .venv Python：路徑存在且必要套件可 import，缺一即明確失敗。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string[]]$RequiredModules = @("PyInstaller", "requests")
    )
    $python = Resolve-VenvPython -RepoRoot $RepoRoot
    Assert-VenvPythonModules -Python $python -RequiredModules $RequiredModules
    Write-Host "  Build interpreter: $python"
    return $python
}

function Invoke-VenvPython {
    <#
      .SYNOPSIS
      以指定的 .venv Python 執行腳本；非零 exit code 明確中止發布流程。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Stage
    )
    Write-Host "  > $Python $($Arguments -join ' ')"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    $code = 1
    try {
        & $Python @Arguments 2>&1 | Out-Host
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($code -ne 0) {
        Write-Host "[ERROR] [$Stage] $Python 執行失敗（exit $code）→ 已中止發布流程。" -ForegroundColor Red
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



# ── 版本一致性工具（唯一真相來源：src/_version.py 的 __version__）────────
# 衍生值（pyproject.toml [project].version / [tool.commitizen].version /
# uv.lock 專案條目）一律由本腳本同步，不得手動只改其中一個欄位。

function Read-TextFileRaw {
    <#
      .SYNOPSIS 讀取文字檔並保留原始編碼資訊。
      .DESCRIPTION 回傳 @{ Text; HasBom; Bytes }。Text 以 UTF-8 解碼且不含 BOM，
                 原始位元組（含 BOM）完整保存在 Bytes。
    #>
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path $Path)) { throw "檔案不存在：$Path" }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $offset = if ($hasBom) { 3 } else { 0 }
    $text = [System.Text.Encoding]::UTF8.GetString($bytes, $offset, $bytes.Length - $offset)
    return @{ Text = $text; HasBom = $hasBom; Bytes = $bytes }
}

function Write-TextFileRaw {
    <#
      .SYNOPSIS 以完全相同的編碼與 BOM 狀態寫回文字檔。
      .DESCRIPTION 不新增／移除 BOM，不改變換行格式（換行符由 Text 原樣帶入）。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][bool]$HasBom
    )
    $enc = New-Object System.Text.UTF8Encoding($HasBom)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Write-Utf8NoBomText {
    <#
      .SYNOPSIS 固定寫成 UTF-8（無 BOM）。
      .DESCRIPTION Windows PowerShell 5.1 的 -Encoding UTF8 會寫入 BOM，PowerShell 7 不會；
                 本函式在兩者產生完全相同的位元組。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Test-VersionFormat {
    <#
      .SYNOPSIS 驗證版本字串格式。
      .DESCRIPTION 必須為 major.minor.patch（可帶 pre-release 後綴）。
                 正式發布路徑只接受 PEP 440 合法後綴（alpha/a/beta/b/c/pre/preview/rc），
                 因為這些值必須能寫入 pyproject.toml 的 project.version。
                 -AllowNonPep440Suffix 僅供測試倉使用（如 1.2.2-test.1，非 PEP 440 合法值）。
    #>
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Version,
        [switch]$AllowNonPep440Suffix
    )
    if ([string]::IsNullOrWhiteSpace($Version)) { return $false }
    if ($Version -ne $Version.Trim()) { return $false }
    if ($Version -match '\s') { return $false }
    if ($Version -notmatch '^(?<core>\d+\.\d+\.\d+)(?<suffix>-[0-9A-Za-z][0-9A-Za-z.+-]*)?$') { return $false }
    $suffix = $Matches["suffix"]
    if ([string]::IsNullOrEmpty($suffix)) { return $true }
    if ($suffix -match '^-(alpha|a|beta|b|c|pre|preview|rc)(\.\d+)?$') { return $true }
    if ($AllowNonPep440Suffix) { return $true }
    return $false
}

function Get-TomlSectionValue {
    <#
      .SYNOPSIS 取出 TOML 某個 section 某個 key 的所有值。
      .OUTPUT 陣列，每筆為 @{ Value; LineNumber }；找不到時為空陣列。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Content,
        [Parameter(Mandatory = $true)][string]$Section,
        [Parameter(Mandatory = $true)][string]$Key
    )
    $lines = $Content -split "`r?`n"
    $current = $null
    $hits = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $t = $lines[$i].Trim()
        if ($t -match '^\[(?<name>[^\[\]]+)\]$') { $current = $Matches["name"].Trim(); continue }
        if ($current -eq $Section -and $t -match '^(?<key>[A-Za-z0-9_-]+)\s*=\s*"(?<value>[^"]*)"$') {
            if ($Matches["key"] -eq $Key) {
                $hits += [pscustomobject]@{ Value = $Matches["value"]; LineNumber = ($i + 1) }
            }
        }
    }
    return $hits
}

function Set-TomlSectionValue {
    <#
      .SYNOPSIS 精準取代 TOML 某個 section 某個 key 的值。
      .DESCRIPTION 只接受「整行僅有 key = "value"」的樣式，且命中數必須恰好為 1，
                 否則丟出錯誤。僅取代引號內的值，其餘位元組（含換行與縮排）原樣保留。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Content,
        [Parameter(Mandatory = $true)][string]$Section,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$NewValue
    )
    $valuePattern = '(?m)^(?<lead>[^\S\r\n]*' + [regex]::Escape($Key) + '[^\S\r\n]*=[^\S\r\n]*")(?<value>[^"\r\n]*)(?<tail>"[^\S\r\n]*)\r?$'
    $sectionPattern = '(?ms)^\[' + [regex]::Escape($Section) + '\][^\S\r\n]*\r?$(?<body>.*?)(?=^\[|\z)'
    $sectionMatch = [regex]::Match($Content, $sectionPattern)
    if (-not $sectionMatch.Success) { throw "pyproject.toml 找不到 section [$Section]" }
    $body = $sectionMatch.Groups["body"].Value
    $hits = [regex]::Matches($body, $valuePattern)
    if ($hits.Count -ne 1) { throw "pyproject.toml [$Section].$Key 命中數量 = $($hits.Count)（必須為 1）" }
    $valueGroup = $hits[0].Groups["value"]
    $newBody = $body.Remove($valueGroup.Index, $valueGroup.Length).Insert($valueGroup.Index, $NewValue)
    return $Content.Remove($sectionMatch.Groups["body"].Index, $sectionMatch.Groups["body"].Length).Insert($sectionMatch.Groups["body"].Index, $newBody)
}

function Get-VersionFromVersionFile {
    <# 讀取 src/_version.py 的 __version__（命中數必須為 1）。 #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $raw = Read-TextFileRaw -Path (Join-Path $RepoRoot "src\_version.py")
    $pattern = '(?m)^[^\S\r\n]*__version__[^\S\r\n]*=[^\S\r\n]*"(?<value>[^"\r\n]*)"[^\S\r\n]*\r?$'
    $hits = [regex]::Matches($raw.Text, $pattern)
    if ($hits.Count -ne 1) { throw "src/_version.py 的 __version__ 命中數量 = $($hits.Count)（必須為 1）" }
    return $hits[0].Groups["value"].Value
}

function Get-UvLockProjectVersion {
    <# 解析 uv.lock 中專案條目的版本；找不到回傳 $null。 #>
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string]$ProjectName = "gametools-health-monitor"
    )
    $lockPath = Join-Path $RepoRoot "uv.lock"
    if (-not (Test-Path $lockPath)) { return $null }
    $lines = [System.IO.File]::ReadAllLines($lockPath)
    $name = $null
    $version = $null
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -eq "[[package]]") { $name = $null; $version = $null; continue }
        if ($null -eq $name -and $t -match '^name\s*=\s*"(?<v>[^"]*)"$') { $name = $Matches["v"]; continue }
        if ($null -eq $version -and $t -match '^version\s*=\s*"(?<v>[^"]*)"$') { $version = $Matches["v"]; continue }
        if ($name -eq $ProjectName -and $version) { return $version }
    }
    if ($name -eq $ProjectName -and $version) { return $version }
    return $null
}

function Get-VersionSources {
    <# 回傳四個版本來源的字典（來源名稱 → 值；缺漏為 $null）。 #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $projectVersion = $null
    $czVersion = $null
    $pyprojectPath = Join-Path $RepoRoot "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        $raw = Read-TextFileRaw -Path $pyprojectPath
        $pHits = @(Get-TomlSectionValue -Content $raw.Text -Section "project" -Key "version")
        if ($pHits.Count -eq 1) { $projectVersion = $pHits[0].Value }
        $cHits = @(Get-TomlSectionValue -Content $raw.Text -Section "tool.commitizen" -Key "version")
        if ($cHits.Count -eq 1) { $czVersion = $cHits[0].Value }
    }
    return [ordered]@{
        "src/_version.py"                   = (Get-VersionFromVersionFile -RepoRoot $RepoRoot)
        "pyproject.toml [project]"          = $projectVersion
        "pyproject.toml [tool.commitizen]"  = $czVersion
        "uv.lock"                           = (Get-UvLockProjectVersion -RepoRoot $RepoRoot)
    }
}

function Test-VersionConsistency {
    <#
      .SYNOPSIS 檢查四個版本來源是否一致。
      .OUTPUT @{ Ok; Sources; Expected; Distinct; Missing }
    #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $sources = Get-VersionSources -RepoRoot $RepoRoot
    # uv.lock 受 Git 追蹤（依賴鎖定檔，必須納入 release commit）：檔案不存在時視為「不適用」而非「不一致」；
    # 檔案存在但專案條目版本不符 → 一律視為不一致。
    $uvLockExists = Test-Path (Join-Path $RepoRoot "uv.lock")
    $items = @()
    foreach ($key in $sources.Keys) {
        $applicable = $true
        if ($key -eq "uv.lock") { $applicable = $uvLockExists }
        $items += [pscustomobject]@{ Name = $key; Value = $sources[$key]; Applicable = $applicable }
    }
    $effective = @($items | Where-Object { $_.Applicable })
    $values = @($effective | ForEach-Object { $_.Value } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $distinct = @($values | Select-Object -Unique)
    $missing = @($effective | Where-Object { [string]::IsNullOrWhiteSpace($_.Value) })
    $ok = ($missing.Count -eq 0) -and ($distinct.Count -eq 1)
    return [pscustomobject]@{
        Ok       = $ok
        Sources  = $items
        Effective = $effective.Count
        Expected = $(if ($distinct.Count -eq 1) { $distinct[0] } else { $null })
        Distinct = $distinct
        Missing  = $missing.Name
    }
}

function Show-VersionConsistencyReport {
    <# 輸出版本不一致的差異表（欄位／實際值／預期值）。 #>
    param([Parameter(Mandatory = $true)]$Result)
    Write-Host "[ERROR] 版本一致性檢查失敗：四個版本來源不一致，已中止發布流程。" -ForegroundColor Red
    Write-Host "        預期版本：$($Result.Expected)" -ForegroundColor Red
    foreach ($s in $Result.Sources) {
        $flag = if ($s.Value -eq $Result.Expected) { "   " } else { " ->" }
        Write-Host "  $flag $($s.Name) = $($s.Value)" -ForegroundColor Red
    }
    if ($Result.Missing.Count -gt 0) {
        Write-Host "  -> 缺少版本值的來源：$($Result.Missing -join ', ')" -ForegroundColor Red
    }
    foreach ($s in @($Result.Sources | Where-Object { -not $_.Applicable })) {
        Write-Host "     $($s.Name)：檔案不存在，略過該來源檢查" -ForegroundColor DarkGray
    }
}

function Sync-VersionFields {
    <#
      .SYNOPSIS 同步版本欄位（src/_version.py ＋ pyproject.toml 兩處）。
      .DESCRIPTION 每個欄位必須恰好命中一次；先驗證全部欄位再寫入（不得留下半套版本）；
                 寫入保留原編碼／BOM／換行；寫完重新讀取驗證；任一步失敗即丟出例外。
                 -OnlyVersionFile：只改 src/_version.py（測試倉用，測試版號非 PEP 440 合法值）。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$NewVersion,
        [switch]$OnlyVersionFile
    )
    # ── 階段 1：驗證全部目標欄位並計算新內容（尚未寫入任何檔案）──
    # 先驗證後寫入：任一欄位命中數異常時直接中止，不得留下半套版本。
    $versionFile = Join-Path $RepoRoot "src\_version.py"
    $raw = Read-TextFileRaw -Path $versionFile
    $pattern = '(?m)^(?<lead>[^\S\r\n]*__version__[^\S\r\n]*=[^\S\r\n]*")(?<value>[^"\r\n]*)(?<tail>"[^\S\r\n]*)\r?$'
    $hits = [regex]::Matches($raw.Text, $pattern)
    if ($hits.Count -ne 1) { throw "src/_version.py 的 __version__ 命中數量 = $($hits.Count)（必須為 1）" }
    $valueGroup = $hits[0].Groups["value"]
    $newVersionText = $raw.Text.Remove($valueGroup.Index, $valueGroup.Length).Insert($valueGroup.Index, $NewVersion)

    $pyprojectPath = $null
    $rawPy = $null
    $newPyText = $null
    if (-not $OnlyVersionFile) {
        $pyprojectPath = Join-Path $RepoRoot "pyproject.toml"
        $rawPy = Read-TextFileRaw -Path $pyprojectPath
        $newPyText = $rawPy.Text
        foreach ($section in @("project", "tool.commitizen")) {
            $sectionHits = @(Get-TomlSectionValue -Content $newPyText -Section $section -Key "version")
            if ($sectionHits.Count -ne 1) { throw "pyproject.toml [$section].version 命中數量 = $($sectionHits.Count)（必須為 1）" }
            $newPyText = [string](Set-TomlSectionValue -Content $newPyText -Section $section -Key "version" -NewValue $NewVersion)
        }
    }

    # ── 階段 2：寫入（所有目標欄位皆已驗證通過）────────────────
    Write-TextFileRaw -Path $versionFile -Text $newVersionText -HasBom $raw.HasBom
    if (-not $OnlyVersionFile) {
        Write-TextFileRaw -Path $pyprojectPath -Text $newPyText -HasBom $rawPy.HasBom
    }

    # 3) 重新讀取驗證
    $sources = Get-VersionSources -RepoRoot $RepoRoot
    $expectedKeys = @("src/_version.py")
    if (-not $OnlyVersionFile) { $expectedKeys += @("pyproject.toml [project]", "pyproject.toml [tool.commitizen]") }
    foreach ($key in $expectedKeys) {
        if ($sources[$key] -ne $NewVersion) { throw "版本同步驗證失敗：$key = '$($sources[$key])'（預期 $NewVersion）" }
    }
}

function Invoke-UvLockUpdate {
    <#
      .SYNOPSIS 以 uv lock 重產生 lockfile，並以 uv lock --check 驗證。
      .DESCRIPTION 檢查 uv 是否存在、檢查退出碼（非只看輸出文字）；失敗即丟出例外。
    #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "找不到 uv 指令（請先安裝 uv）" }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $PSNativeCommandUseErrorActionPreference = $false
    Push-Location $RepoRoot
    try {
        & uv lock 2>&1 | Out-Host
        $lockCode = $LASTEXITCODE
        if ($lockCode -ne 0) { throw "uv lock 失敗（exit $lockCode）" }
        & uv lock --check 2>&1 | Out-Host
        $checkCode = $LASTEXITCODE
        if ($checkCode -ne 0) { throw "uv lock --check 失敗（exit $checkCode）" }
    } finally {
        Pop-Location
        $ErrorActionPreference = $prevEap
    }
}

function New-FileBackup {
    <#
      .SYNOPSIS 位元組級備份單一檔案（不做文字序列化，完整保留 BOM / 換行 / 原始編碼）。
      .OUTPUT @{ Path; Existed; Bytes }；檔案不存在時 Existed=$false、Bytes=$null。
    #>
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    if (Test-Path -LiteralPath $full) {
        return @{ Path = $full; Existed = $true; Bytes = [System.IO.File]::ReadAllBytes($full) }
    }
    return @{ Path = $full; Existed = $false; Bytes = $null }
}

function Restore-FileBackup {
    <#
      .SYNOPSIS 還原檔案備份；原本不存在的檔案會被刪除（回到「不存在」狀態）。
      .OUTPUT @{ Ok; Failures }
    #>
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Backups
    )
    $failures = @()
    foreach ($b in $Backups) {
        try {
            if ($b.Existed) {
                [System.IO.File]::WriteAllBytes($b.Path, $b.Bytes)
            } elseif (Test-Path -LiteralPath $b.Path) {
                [System.IO.File]::Delete($b.Path)
            }
        } catch {
            $failures += [pscustomobject]@{ Path = $b.Path; Error = $_.Exception.Message }
        }
    }
    return @{ Ok = ($failures.Count -eq 0); Failures = $failures }
}

function Test-FileBackupRestored {
    <# 驗證檔案已回到備份當下的位元組狀態（逐位元組比對）。 #>
    param([Parameter(Mandatory = $true)]$Backup)
    if (-not $Backup.Existed) { return (-not (Test-Path -LiteralPath $Backup.Path)) }
    if (-not (Test-Path -LiteralPath $Backup.Path)) { return $false }
    $now = [System.IO.File]::ReadAllBytes($Backup.Path)
    if ($null -eq $now -or $now.Length -ne $Backup.Bytes.Length) { return $false }
    for ($i = 0; $i -lt $now.Length; $i++) {
        if ($now[$i] -ne $Backup.Bytes[$i]) { return $false }
    }
    return $true
}

function Write-ReleaseFailureReport {
    <#
      .SYNOPSIS 寫出發布失敗報告到 %TEMP% 下的專案專屬目錄，並回傳報告路徑。
      .DESCRIPTION 報告放在使用者資料區（不在 repo 內），不會被誤加入 release commit。
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][string]$Reason,
        [object[]]$Modified = @(),
        [object[]]$Restored = @(),
        [object[]]$RestoreFailures = @(),
        [string]$RetryCommand = "",
        [string[]]$ManualSteps = @()
    )
    $dir = Join-Path $env:TEMP "GameTools_HealthMonitor\release_failures"
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = Join-Path $dir "release_failed-$stamp.log"
    $modifiedText = "（無）"
    if ($Modified.Count -gt 0) { $modifiedText = $Modified -join ", " }
    $restoredText = "（無）"
    if ($Restored.Count -gt 0) { $restoredText = $Restored -join ", " }
    $lines = @()
    $lines += "時間：" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $lines += "階段：$Stage"
    $lines += "原因：$Reason"
    $lines += "已修改檔案：$modifiedText"
    $lines += "已還原檔案：$restoredText"
    if ($RestoreFailures.Count -gt 0) {
        $lines += "還原失敗檔案："
        foreach ($f in $RestoreFailures) { $lines += ("  - " + $f.Path + " → " + $f.Error) }
    } else {
        $lines += "還原失敗檔案：（無）"
    }
    if ($RetryCommand) { $lines += "重試命令：$RetryCommand" }
    foreach ($s in $ManualSteps) { $lines += "  $s" }
    $text = ($lines -join [Environment]::NewLine) + [Environment]::NewLine
    [System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))
    return $path
}

function Invoke-VersionSyncRollback {
    <#
      .SYNOPSIS 版本同步階段失敗時：位元組級還原 + 寫出失敗報告。
      .OUTPUT @{ ReportPath; Ok; Modified; Restored; Failures }
    #>
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Backups,
        [Parameter(Mandatory = $true)][string]$Stage,
        [Parameter(Mandatory = $true)][string]$Reason,
        [string]$RetryCommand = "",
        [string[]]$ManualSteps = @()
    )
    $modified = @()
    foreach ($b in $Backups) {
        if (-not (Test-FileBackupRestored -Backup $b)) {
            $modified += (Split-Path -Path $b.Path -Leaf)
        }
    }
    $restore = Restore-FileBackup -Backups $Backups
    $restored = @()
    $failures = @($restore.Failures)
    foreach ($b in $Backups) {
        $leaf = Split-Path -Path $b.Path -Leaf
        if (Test-FileBackupRestored -Backup $b) {
            if ($modified -contains $leaf) { $restored += $leaf }
        } else {
            $known = $failures | Where-Object { (Split-Path -Path $_.Path -Leaf) -eq $leaf }
            if (-not $known) {
                $failures += [pscustomobject]@{ Path = $leaf; Error = "還原後位元組仍與原始狀態不一致" }
            }
        }
    }
    $reportPath = Write-ReleaseFailureReport -Stage $Stage -Reason $Reason -Modified $modified -Restored $restored -RestoreFailures $failures -RetryCommand $RetryCommand -ManualSteps $ManualSteps
    return @{ ReportPath = $reportPath; Ok = ($failures.Count -eq 0); Modified = $modified; Restored = $restored; Failures = $failures }
}

function Assert-VersionConsistency {
    <#
      .SYNOPSIS 一致性閘門：不一致即列出差異並回傳 $false（由呼叫端決定是否回滾並中止）。
    #>
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $result = Test-VersionConsistency -RepoRoot $RepoRoot
    if (-not $result.Ok) {
        Show-VersionConsistencyReport -Result $result
        Write-Host "        未執行 git add / commit / tag / push / GitHub Release。" -ForegroundColor Red
        return $false
    }
    Write-Host "  版本一致性檢查通過（$($result.Effective) 個來源皆為 $($result.Expected)）" -ForegroundColor DarkGray
    return $true
}
# 測試倉（-TestRepo 模式的 Velopack 資產與 Release 目的地）
$testRepoSlug = "Sid-1996/PathofExile-Sid-GameTools_HealthMonitor_release-test"

# 測試倉模式下 src/_version.py 的原始位元組（腳本結束時自動還原）
$script:TestRepoVersionBackup = $null

try {
    # ── 讀取當前版本（唯一真相來源：src/_version.py 的 __version__）────────────
    $currentVersion = ""
    try {
        $currentVersion = Get-VersionFromVersionFile -RepoRoot $PSScriptRoot
    } catch {
        Write-Host "[ERROR] 無法讀取版本：$($_.Exception.Message)" -ForegroundColor Red
        Write-Host "        請確認 src/_version.py 存在且 __version__ 格式正確；已中止發布流程。" -ForegroundColor Red
        exit 1
    }
    Write-Host "  目前版本（src/_version.py）：$currentVersion"

    # ── 版本格式驗證（任何檔案寫入之前）──────────────────────────────
    if ($Version) {
        # 測試倉允許非 PEP 440 後綴（1.2.2-test.1），但正式發布路徑不允許：
        # 非 PEP 440 合法值無法寫入 pyproject.toml 的 project.version。
        $allowNonPep440 = [bool]$TestRepo
        if (-not (Test-VersionFormat -Version $Version -AllowNonPep440Suffix:$allowNonPep440)) {
            Write-Host "[ERROR] 版本格式無效：'$Version'" -ForegroundColor Red
            Write-Host "        必須為 major.minor.patch（如 1.5.0）；pre-release 僅接受 alpha/a/beta/b/c/pre/preview/rc。" -ForegroundColor Red
            Write-Host "        已中止：未寫入任何檔案、未 staging、未 commit / tag / push。" -ForegroundColor Red
            exit 1
        }
    }

    # ── 版本同步（冪等）：只要指定 -Version 就完整跑一次同步 + lock ──────────
    # 舊版以「版本是否變化」決定是否同步，導致 uv lock 失敗後以同一命令重試會跳過
    # 同步，最後一致性閘門必然失敗（永久卡住）。現在只要有 -Version 就重跑，
    # 同步本身冪等，失敗可直接用同一命令重試。
    # -StageOnly 是唯讀自我檢查，不改動任何檔案。
    $versionSyncRequested = ([bool]$Version -and (-not $StageOnly))
    $syncBackups = @()
    $syncStage = "版本同步"

    if ($TestRepo) {
        # 測試倉刻意讓 _version.py 與 pyproject.toml 分歧 → 閘門必須在分歧之前執行
        if (-not (Assert-VersionConsistency -RepoRoot $PSScriptRoot)) {
            exit 1
        }
    }

    # ── 專案 .venv 檢查（正式建置必須使用鎖定的環境）──
    # 缺 .venv 或缺必要套件時明確中止；絕不退回 PATH 上的系統 Python。
    # 檢查點在「任何版本檔寫入」之前：環境未就緒時不得留下未發布的版本變更。
    # -StageOnly 是唯讀自我檢查（不建置）→ 不需要 .venv。
    # requests 只有 delta（tools/make_delta.py → updater_core）需要；
    # -Preview / -TestRepo 不執行 delta，故只要求 PyInstaller。
    $venvPython = ""
    if (-not $StageOnly) {
        $buildModules = @("PyInstaller")
        if (-not $Preview -and -not $TestRepo) { $buildModules += "requests" }
        $venvPython = Resolve-BuildPython -RepoRoot $PSScriptRoot -RequiredModules $buildModules
    }

    if ($versionSyncRequested) {
        Write-Host "[1/7] Updating version: $currentVersion → $Version"
        # ── 位元組級備份（失敗時必須能完整還原；原本不存在也要記錄）──
        if ($TestRepo) {
            $syncBackups = @((New-FileBackup -Path (Join-Path $PSScriptRoot "src\_version.py")))
            $script:TestRepoVersionBackup = $syncBackups[0]
        } else {
            $syncBackups = @(
                (New-FileBackup -Path (Join-Path $PSScriptRoot "src\_version.py"))
                (New-FileBackup -Path (Join-Path $PSScriptRoot "pyproject.toml"))
                (New-FileBackup -Path (Join-Path $PSScriptRoot "uv.lock"))
            )
        }
        $retryCommand = ".\release.ps1 -Version $Version"
        if ($TestRepo) { $retryCommand = ".\release.ps1 -TestRepo -Version $Version" }
        try {
            if ($TestRepo) {
                Sync-VersionFields -RepoRoot $PSScriptRoot -NewVersion $Version -OnlyVersionFile
                Write-Host "  [TestRepo] 僅更新 src/_version.py；pyproject.toml / uv.lock 不動（測試版號非 PEP 440 合法值）" -ForegroundColor Yellow
                Write-Host "  [TestRepo] 測試版號會在腳本結束時自動還原 src/_version.py" -ForegroundColor Yellow
            } else {
                Sync-VersionFields -RepoRoot $PSScriptRoot -NewVersion $Version
                $syncStage = "uv lock"
                Invoke-UvLockUpdate -RepoRoot $PSScriptRoot
            }
        } catch {
            $reason = $_.Exception.Message
            $rb = Invoke-VersionSyncRollback -Backups $syncBackups -Stage $syncStage -Reason $reason -RetryCommand $retryCommand
            Write-Host "[ERROR] 版本同步失敗：$reason" -ForegroundColor Red
            if ($rb.Ok) {
                Write-Host "        已回滾至執行前狀態（逐位元組驗證通過）：$($rb.Restored -join ', ')" -ForegroundColor Yellow
            } else {
                Write-Host "        回滾未完全成功，需人工復原：" -ForegroundColor Red
                foreach ($f in $rb.Failures) { Write-Host ("          - " + $f.Path + " → " + $f.Error) -ForegroundColor Red }
            }
            Write-Host "        失敗報告：$($rb.ReportPath)" -ForegroundColor Yellow
            Write-Host "        已中止：未執行 git add / commit / tag / push / GitHub Release。" -ForegroundColor Red
            exit 1
        }
        $currentVersion = $Version
    } else {
        Write-Host "[1/7] Using current version: $currentVersion"
    }

    # ── 發布前一致性閘門（任何 staging / commit / tag / push / GitHub Release 之前）──
    if (-not $TestRepo) {
        if (-not (Assert-VersionConsistency -RepoRoot $PSScriptRoot)) {
            if ($syncBackups.Count -gt 0) {
                $rb = Invoke-VersionSyncRollback -Backups $syncBackups -Stage "版本一致性閘門" -Reason "四個版本來源不一致" -RetryCommand ".\release.ps1 -Version $Version"
                if ($rb.Ok) {
                    Write-Host "        已回滾至執行前狀態（逐位元組驗證通過）：$($rb.Restored -join ', ')" -ForegroundColor Yellow
                } else {
                    Write-Host "        回滾未完全成功，需人工復原：" -ForegroundColor Red
                    foreach ($f in $rb.Failures) { Write-Host ("          - " + $f.Path + " → " + $f.Error) -ForegroundColor Red }
                }
            } else {
                $rb = Invoke-VersionSyncRollback -Backups @() -Stage "版本一致性閘門" -Reason "四個版本來源不一致" -RetryCommand "uv lock" -ManualSteps @("本次未執行版本同步，無檔案可回滾；請先執行 uv lock 重新產生 lockfile 後再重跑")
                Write-Host "        本次未執行版本同步，無檔案可回滾。" -ForegroundColor Yellow
            }
            Write-Host "        失敗報告：$($rb.ReportPath)" -ForegroundColor Yellow
            exit 1
        }
    }

    # ── StageOnly：只做 staging 自我檢查（不動版本、不建置、不 commit / push / tag）──
if ($StageOnly) {
    Write-Host "`n[StageOnly] 僅執行發布 staging 自我檢查（不建置 / 不 commit / 不 push / 不 tag）"
    Invoke-ReleaseStage
    Write-Host "`n[StageOnly] staging 檢查完成" -ForegroundColor Cyan
    exit 0
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
        Write-Utf8NoBomText -Path $preFile -Text "$currentVersion`n"
        Write-Host "  latest_version_prerelease.txt → $currentVersion (preview)"
        Write-Host "  latest_version.txt unchanged"
    } else {
        Write-Utf8NoBomText -Path (Join-Path $PSScriptRoot "latest_version.txt") -Text "$currentVersion`n"
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
# 正式建置一律使用專案鎖定的 .venv Python（$venvPython 已於發布前檢查）
$buildScript = Join-Path $PSScriptRoot "tools\build.py"
Invoke-VenvPython -Python $venvPython -Arguments @($buildScript) -Stage "build"

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
        # delta 必須與 build 使用同一個 .venv Python
        Invoke-VenvPython -Python $venvPython -Arguments @($makeDelta, $currentVersion, $baseVersion, $packageDirForDelta, (Join-Path $PSScriptRoot "dist")) -Stage "make_delta"
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
    Write-Host " [提醒] _version.py 暫時改為 $currentVersion（測試版號），腳本結束時會自動還原。" -ForegroundColor Yellow
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
}
finally {
    # ── 測試倉模式：無論成功或失敗都必須還原 src/_version.py ──────────────
    # 測試版號只是暫時寫入，結束後必須回到執行前的位元組狀態；
    # 還原失敗不得回報測試倉發布成功。
    if ($null -ne $script:TestRepoVersionBackup) {
        $restore = Restore-FileBackup -Backups @($script:TestRepoVersionBackup)
        $verified = $true
        foreach ($b in @($script:TestRepoVersionBackup)) {
            if (-not (Test-FileBackupRestored -Backup $b)) { $verified = $false }
        }
        if ($restore.Ok -and $verified) {
            Write-Host "  [TestRepo] src/_version.py 已還原為執行前狀態（逐位元組驗證通過）" -ForegroundColor Cyan
        } else {
            $restoreFailures = @($restore.Failures)
            if ($restoreFailures.Count -eq 0) {
                $restoreFailures = @([pscustomobject]@{ Path = "src/_version.py"; Error = "還原後位元組仍與原始狀態不一致" })
            }
            $reportPath = Write-ReleaseFailureReport -Stage "TestRepo 還原" -Reason "測試倉流程結束後還原 src/_version.py 失敗" -Modified @("src/_version.py") -Restored @() -RestoreFailures $restoreFailures -ManualSteps @("手動還原：git restore -- src/_version.py")
            Write-Host "[ERROR] [TestRepo] src/_version.py 還原失敗，測試倉發布視為失敗。" -ForegroundColor Red
            foreach ($f in $restoreFailures) { Write-Host ("        - " + $f.Path + " → " + $f.Error) -ForegroundColor Red }
            Write-Host "        失敗報告：$reportPath" -ForegroundColor Yellow
            exit 1
        }
    }
}
