# cleanup.ps1 - 清理建置/打包產物
# 用法:
#   .\scripts\cleanup.ps1          # 清 PyInstaller 暫存、發布 ZIP；dist\vpk 只保留最新一版 full+delta nupkg 與 feed 三件套（保住 delta 鏈）
#   .\scripts\cleanup.ps1 -All     # 連 dist\vpk 與 dist\GameTools_Package 全清（發正式版前用；首版無 delta 屬正常）
# 相容 PowerShell 5.1 與 7。Join-Path 一律單串二段，避免 PositionalParameterNotFound。
param(
    [switch]$All
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $repoRoot "dist"
$vpkDir = Join-Path $distDir "vpk"
$packageDir = Join-Path $distDir "GameTools_Package"
$removedBytes = 0

function Remove-PathSafe {
    param([string]$Path, [string]$Label)
    if (Test-Path $Path) {
        $size = 0
        $item = Get-Item $Path -Force
        if ($item.PSIsContainer) {
            $size = (Get-ChildItem $Path -Recurse -File -Force | Measure-Object Length -Sum).Sum
            Remove-Item $Path -Recurse -Force -Confirm:$false
        } else {
            $size = $item.Length
            Remove-Item $Path -Force -Confirm:$false
        }
        $script:removedBytes += $size
        Write-Host ("  已刪除 {0}  (釋放 {1:N1} MB)" -f $Label, ($size / 1MB)) -ForegroundColor Gray
    }
}

function Get-NupkgVersion {
    # 從檔名 Sid.GameToolsHealthMonitor-<version>-full|delta.nupkg 抽出版本字串
    param([string]$FileName)
    if ($FileName -match '^Sid\.GameToolsHealthMonitor-(.+)-(full|delta)\.nupkg$') {
        return $Matches[1]
    }
    return $null
}

Write-Host "========================================"
Write-Host " 清理建置/打包產物"
Write-Host "========================================"

# 1) PyInstaller 工作暫存
Write-Host "`n[1] PyInstaller 工作暫存..."
Get-ChildItem (Join-Path $repoRoot "build") -Directory -Filter "pyinstaller_work_*" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-PathSafe -Path $_.FullName -Label $_.Name }

# 2) 舊鏈發布 ZIP
Write-Host "`n[2] 舊鏈發布 ZIP..."
Get-ChildItem $distDir -File -Filter "GameTools_HealthMonitor_v*_*.zip" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-PathSafe -Path $_.FullName -Label $_.Name }

# 3) 其他暫存
Write-Host "`n[3] 其他暫存..."
Remove-PathSafe -Path (Join-Path $repoRoot ".tmp.driveupload") -Label ".tmp.driveupload"

# 4) dist\vpk
if ($All) {
    Write-Host "`n[4] dist\vpk 全清（-All）..."
    Remove-PathSafe -Path $vpkDir -Label "dist\vpk"
} elseif (Test-Path $vpkDir) {
    Write-Host "`n[4] dist\vpk 瘦身（保留最新一版 full+delta 與 feed 三件套）..."
    $feedFiles = @("releases.win.json", "releases.osx.json", "RELEASES", "assets.win.json", "assets.osx.json")
    $nupkgs = Get-ChildItem $vpkDir -File -Filter "*.nupkg" -ErrorAction SilentlyContinue
    if ($nupkgs) {
        # 找出最新版本（正式版 > 帶後綴的 pre-release）
        $latest = $nupkgs | ForEach-Object { Get-NupkgVersion -FileName $_.Name } |
            Where-Object { $_ } | Sort-Object { [version]($_ -replace '-.*$', '') } -Descending |
            Sort-Object { if ($_ -match '-') { 1 } else { 0 } } | Select-Object -First 1
        if ($latest) {
            Write-Host ("  保留版本: {0}" -f $latest)
            foreach ($f in $nupkgs) {
                $v = Get-NupkgVersion -FileName $f.Name
                if ($v -and $v -ne $latest) {
                    Remove-PathSafe -Path $f.FullName -Label $f.Name
                }
            }
        }
    }
    # feed 三件套一律保留
    foreach ($feed in $feedFiles) {
        $p = Join-Path $vpkDir $feed
        if (Test-Path $p) { Write-Host ("  保留 feed: {0}" -f $feed) }
    }
}

# 5) dist\GameTools_Package
if ($All) {
    Write-Host "`n[5] dist\GameTools_Package 全清（-All）..."
    Remove-PathSafe -Path $packageDir -Label "dist\GameTools_Package"
}

Write-Host ""
if ($removedBytes -gt 0) {
    Write-Host ("清理完成，共釋放 {0:N1} MB" -f ($removedBytes / 1MB)) -ForegroundColor Green
} else {
    Write-Host "沒有可清理的項目。" -ForegroundColor Green
}