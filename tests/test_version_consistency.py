"""版本一致性測試（Phase 4C-3B）。

涵蓋三個面向：

1. release.ps1 的版本欄位同步與發布前一致性閘門。
   PowerShell 測試一律在隔離 sandbox 內執行：以 AST 從 release.ps1 擷取真實函式再呼叫，
   不操作正式 repo 的 index / tag / remote。
2. latest_version.txt / latest_version_prerelease.txt 的 UTF-8 BOM 已清除，
   且 Windows PowerShell 5.1 與 PowerShell 7 寫出的位元組完全一致。
3. src/updater_core._parse_version() 容忍開頭的 UTF-8 BOM。

唯一真相來源是 src/_version.py 的 __version__；pyproject.toml 兩處與 uv.lock
專案條目都是衍生值，必須與它一致。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from updater_core import _parse_version

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_PS1 = REPO_ROOT / "release.ps1"

PWSH = shutil.which("pwsh")
POWERSHELL_51 = shutil.which("powershell.exe")
REAL_GIT = shutil.which("git")

requires_pwsh = pytest.mark.skipif(PWSH is None, reason="pwsh（PowerShell 7）不可用")
requires_ps51 = pytest.mark.skipif(POWERSHELL_51 is None, reason="Windows PowerShell 5.1 不可用")
requires_git = pytest.mark.skipif(REAL_GIT is None, reason="git 不可用")

LF = "[char]10"
CRLF = "[char]13 + [char]10"

# 從 release.ps1 擷取的函式（AST 擷取，非重新實作）
PS_FUNCTIONS = [
    "Read-TextFileRaw",
    "Write-TextFileRaw",
    "Write-Utf8NoBomText",
    "Test-VersionFormat",
    "Get-TomlSectionValue",
    "Set-TomlSectionValue",
    "Get-VersionFromVersionFile",
    "Get-UvLockProjectVersion",
    "Get-VersionSources",
    "Test-VersionConsistency",
    "Show-VersionConsistencyReport",
    "Sync-VersionFields",
    "Invoke-UvLockUpdate",
    "New-FileBackup",
    "Restore-FileBackup",
    "Test-FileBackupRestored",
    "Write-ReleaseFailureReport",
    "Invoke-VersionSyncRollback",
]

EXTRACT_SCRIPT = r"""
param([string]$ReleasePs1, [string]$OutFile, [string]$Names)
$ErrorActionPreference = "Stop"
$errors = $null
$tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($ReleasePs1, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "release.ps1 parse failed" }
$defs = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
$sb = New-Object System.Text.StringBuilder
foreach ($name in $Names.Split(",")) {
    $f = $defs | Where-Object { $_.Name -eq $name }
    if (-not $f) { throw "function not found: $name" }
    [void]$sb.AppendLine($f.Extent.Text)
    [void]$sb.AppendLine("")
}
[System.IO.File]::WriteAllText($OutFile, $sb.ToString(), (New-Object System.Text.UTF8Encoding($true)))
"""

DRIVER_HEADER = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
. $env:PS_FUNCS
"""


def run_ps(body, tmp_path, *, shell=None, env=None):
    """在隔離 temp 目錄執行 PowerShell 片段，回傳 (returncode, stdout, stderr)。"""
    script = tmp_path / "driver.ps1"
    script.write_text(DRIVER_HEADER + body, encoding="utf-8-sig")
    exe = shell or PWSH
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=full_env,
        cwd=str(tmp_path),
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture(scope="session")
def ps_funcs(tmp_path_factory):
    """從 release.ps1 以 AST 擷取真實函式到一個可 dot-source 的 .ps1。"""
    out = tmp_path_factory.mktemp("ps_funcs")
    script = out / "extract.ps1"
    script.write_text(EXTRACT_SCRIPT, encoding="utf-8-sig")
    target = out / "release_funcs.ps1"
    proc = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(script), str(RELEASE_PS1), str(target), ",".join(PS_FUNCTIONS)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, "函式擷取失敗：" + proc.stdout + "\n" + proc.stderr
    return target


def write_sandbox(root, *, version="1.4.0", cz_version="1.4.0", with_uv_lock=True):
    """建立最小 sandbox repo：src/_version.py + pyproject.toml（+ uv.lock）。"""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "_version.py").write_text(
        '# Single source of truth for version\n__version__ = "' + version + '"\n',
        encoding="utf-8",
    )
    pyproject = (
        "[project]\n"
        'name = "gametools-health-monitor"\n'
        'version = "' + version + '"\n'
        'description = "test"\n'
        "\n"
        "[tool.commitizen]\n"
        'name = "cz_conventional_commits"\n'
        'version = "' + cz_version + '"\n'
        'version_files = [\n    "src/_version.py:__version__",\n]\n'
    )
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8", newline="\n")
    if with_uv_lock:
        (root / "uv.lock").write_text(
            '[[package]]\nname = "gametools-health-monitor"\nversion = "' + version + '"\nsource = { virtual = "." }\n',
            encoding="utf-8",
            newline="\n",
        )
    return root


@pytest.fixture
def sandbox(tmp_path):
    return write_sandbox(tmp_path / "repo")


# ── 1. 版本格式驗證 ────────────────────────────────────────────────


@requires_pwsh
def test_version_format_accepts_valid_forms(tmp_path, ps_funcs):
    body = "\n".join(
        [
            '$cases = @("1.5.0", "1.2.2-beta", "1.2.2-beta.1", "1.2.2-rc.1", "10.0.1", "0.0.1")',
            'foreach ($c in $cases) { "$c=" + (Test-VersionFormat -Version $c) }',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs)})
    assert code == 0, err
    for c in ("1.5.0", "1.2.2-beta", "1.2.2-beta.1", "1.2.2-rc.1", "10.0.1", "0.0.1"):
        assert c + "=True" in out, c + " 應被接受：" + out


@requires_pwsh
def test_version_format_rejects_invalid_forms(tmp_path, ps_funcs):
    body = "\n".join(
        [
            '$cases = @("abc", "1.2", "1.2.3.4", "", " 1.2.3", "1.2.3 ", "1.2.3 4", "v1.2.3", "1.2.3-")',
            'foreach ($c in $cases) { "[$c]=" + (Test-VersionFormat -Version $c) }',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs)})
    assert code == 0, err
    for c in ("abc", "1.2", "1.2.3.4", " 1.2.3", "1.2.3 ", "1.2.3 4", "v1.2.3", "1.2.3-"):
        assert "[" + c + "]=False" in out, repr(c) + " 應被拒絕：" + out
    assert "[]=False" in out


@requires_pwsh
def test_version_format_test_suffix_requires_opt_in(tmp_path, ps_funcs):
    """-test.N 這類非 PEP 440 後綴只能給測試倉用（正式發布不允許）。"""
    body = "\n".join(
        [
            '"strict=" + (Test-VersionFormat -Version "1.2.2-test.1")',
            '"allowed=" + (Test-VersionFormat -Version "1.2.2-test.1" -AllowNonPep440Suffix)',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs)})
    assert code == 0, err
    assert "strict=False" in out
    assert "allowed=True" in out


# ── 2. TOML 欄位匹配的精準度 ───────────────────────────────────────


@requires_pwsh
def test_toml_lookup_is_section_scoped(tmp_path, ps_funcs, sandbox):
    """[project].version 與 [tool.commitizen].version 不可互相匹配。"""
    body = "\n".join(
        [
            '$raw = Read-TextFileRaw -Path (Join-Path $env:PS_SANDBOX "pyproject.toml")',
            '$p = @(Get-TomlSectionValue -Content $raw.Text -Section "project" -Key "version")',
            '$c = @(Get-TomlSectionValue -Content $raw.Text -Section "tool.commitizen" -Key "version")',
            '"project_count=$($p.Count);project=$($p[0].Value)"',
            '"cz_count=$($c.Count);cz=$($c[0].Value)"',
            '$missing = @(Get-TomlSectionValue -Content $raw.Text -Section "nope" -Key "version")',
            '"missing_count=$($missing.Count)"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "project_count=1;project=1.4.0" in out
    assert "cz_count=1;cz=1.4.0" in out
    assert "missing_count=0" in out


@requires_pwsh
def test_toml_set_only_changes_target_field(tmp_path, ps_funcs, sandbox):
    body = "\n".join(
        [
            '$path = Join-Path $env:PS_SANDBOX "pyproject.toml"',
            "$raw = Read-TextFileRaw -Path $path",
            '$new = Set-TomlSectionValue -Content $raw.Text -Section "project" -Key "version" -NewValue "2.0.0"',
            "Write-TextFileRaw -Path $path -Text $new -HasBom $raw.HasBom",
            "$raw2 = Read-TextFileRaw -Path $path",
            '$p = @(Get-TomlSectionValue -Content $raw2.Text -Section "project" -Key "version")',
            '$c = @(Get-TomlSectionValue -Content $raw2.Text -Section "tool.commitizen" -Key "version")',
            '"project=$($p[0].Value)"',
            '"cz=$($c[0].Value)"',
            '"bom=$($raw2.HasBom)"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "project=2.0.0" in out
    assert "cz=1.4.0" in out


@requires_pwsh
def test_toml_set_rejects_duplicate_field(tmp_path, ps_funcs, sandbox):
    """命中數不為 1 時必須安全中止（不得寬鬆取代）。"""
    (sandbox / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.4.0"\nversion = "9.9.9"\n', encoding="utf-8")
    body = "\n".join(
        [
            '$raw = Read-TextFileRaw -Path (Join-Path $env:PS_SANDBOX "pyproject.toml")',
            "try {",
            '    $null = Set-TomlSectionValue -Content $raw.Text -Section "project" -Key "version" -NewValue "2.0.0"',
            '    "NO_ERROR"',
            "} catch {",
            '    "CAUGHT"',
            "}",
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "CAUGHT" in out
    assert "NO_ERROR" not in out


# ── 3. 版本同步 ────────────────────────────────────────────────────


@requires_pwsh
def test_sync_updates_all_three_sources(tmp_path, ps_funcs, sandbox):
    body = "\n".join(
        [
            'Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.5.0"',
            "$s = Get-VersionSources -RepoRoot $env:PS_SANDBOX",
            '"version_py=$($s["src/_version.py"])"',
            '"project=$($s["pyproject.toml [project]"])"',
            '"cz=$($s["pyproject.toml [tool.commitizen]"])"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "version_py=1.5.0" in out
    assert "project=1.5.0" in out
    assert "cz=1.5.0" in out


@requires_pwsh
def test_sync_preserves_encoding_and_line_endings(tmp_path, ps_funcs, tmp_path_factory):
    """同步不得改變 BOM 狀態或換行格式。"""
    root = tmp_path_factory.mktemp("enc")
    (root / "src").mkdir()
    (root / "src" / "_version.py").write_bytes(b'\xef\xbb\xbf__version__ = "1.4.0"\r\n')
    (root / "pyproject.toml").write_bytes(b'[project]\nversion = "1.4.0"\n\n[tool.commitizen]\nversion = "1.4.0"\n')
    body = "\n".join(
        [
            'Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.5.0"',
            '$v = [System.IO.File]::ReadAllBytes((Join-Path $env:PS_SANDBOX "src\\_version.py"))',
            '"vbom=" + ($v[0] -eq 0xEF -and $v[1] -eq 0xBB -and $v[2] -eq 0xBF)',
            '"vcrlf=" + ([System.Text.Encoding]::UTF8.GetString($v).Contains(' + CRLF + "))",
            '$p = [System.IO.File]::ReadAllBytes((Join-Path $env:PS_SANDBOX "pyproject.toml"))',
            '"pbom=" + ($p[0] -eq 0xEF -and $p[1] -eq 0xBB -and $p[2] -eq 0xBF)',
            "$pt = [System.Text.Encoding]::UTF8.GetString($p)",
            '"plf=" + ($pt.Contains(' + LF + ") -and -not $pt.Contains(" + CRLF + "))",
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(root)})
    assert code == 0, err
    assert "vbom=True" in out
    assert "vcrlf=True" in out
    assert "pbom=False" in out
    assert "plf=True" in out


@requires_pwsh
def test_sync_aborts_when_field_missing(tmp_path, ps_funcs, sandbox):
    """欄位缺漏時必須中止（不得寫入半套版本）。"""
    (sandbox / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.4.0"\n\n[tool.commitizen]\nname = "cz"\n', encoding="utf-8")
    before = (sandbox / "src" / "_version.py").read_text(encoding="utf-8")
    body = "\n".join(
        [
            "try {",
            '    Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.5.0"',
            '    "NO_ERROR"',
            "} catch {",
            '    "CAUGHT"',
            "}",
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "CAUGHT" in out
    assert "NO_ERROR" not in out
    assert (sandbox / "src" / "_version.py").read_text(encoding="utf-8") == before


@requires_pwsh
def test_sync_only_version_file_skips_pyproject(tmp_path, ps_funcs, sandbox):
    """測試倉模式：只改 _version.py，pyproject.toml 不動。"""
    body = "\n".join(
        [
            'Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.2.2-test.1" -OnlyVersionFile',
            "$s = Get-VersionSources -RepoRoot $env:PS_SANDBOX",
            '"version_py=$($s["src/_version.py"])"',
            '"project=$($s["pyproject.toml [project]"])"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "version_py=1.2.2-test.1" in out
    assert "project=1.4.0" in out


# ── 4. 一致性閘門 ──────────────────────────────────────────────────


@requires_pwsh
def test_consistency_gate_passes_when_all_aligned(tmp_path, ps_funcs, sandbox):
    body = "\n".join(
        [
            "$r = Test-VersionConsistency -RepoRoot $env:PS_SANDBOX",
            '"ok=$($r.Ok);expected=$($r.Expected);effective=$($r.Effective)"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "ok=True;expected=1.4.0" in out


@requires_pwsh
def test_consistency_gate_detects_mismatch(tmp_path, ps_funcs, sandbox):
    pp = sandbox / "pyproject.toml"
    pp.write_text(pp.read_text(encoding="utf-8").replace('version = "1.4.0"', 'version = "9.9.9"', 1), encoding="utf-8")
    body = "\n".join(
        [
            "$r = Test-VersionConsistency -RepoRoot $env:PS_SANDBOX",
            '"ok=$($r.Ok)"',
            "Show-VersionConsistencyReport -Result $r",
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "ok=False" in out
    assert "9.9.9" in out
    assert "1.4.0" in out


@requires_pwsh
def test_consistency_gate_ignores_absent_uv_lock(tmp_path, ps_funcs, sandbox):
    """uv.lock 未受版本控制（.gitignore 排除）；檔案不存在時不得誤判為不一致。"""
    (sandbox / "uv.lock").unlink()
    body = "\n".join(
        [
            "$r = Test-VersionConsistency -RepoRoot $env:PS_SANDBOX",
            '"ok=$($r.Ok);expected=$($r.Expected);effective=$($r.Effective)"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "ok=True;expected=1.4.0" in out


@requires_pwsh
def test_consistency_gate_detects_uv_lock_mismatch(tmp_path, ps_funcs, sandbox):
    lock = sandbox / "uv.lock"
    lock.write_text(lock.read_text(encoding="utf-8").replace('version = "1.4.0"', 'version = "1.3.2"'), encoding="utf-8")
    body = "\n".join(
        [
            "$r = Test-VersionConsistency -RepoRoot $env:PS_SANDBOX",
            '"ok=$($r.Ok)"',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(sandbox)})
    assert code == 0, err
    assert "ok=False" in out


# ── 5. BOM 處理 ────────────────────────────────────────────────────


@requires_pwsh
def test_write_utf8_no_bom_produces_clean_bytes(tmp_path, ps_funcs):
    body = "\n".join(
        [
            'Write-Utf8NoBomText -Path $env:PS_OUT -Text ("1.4.0" + ' + LF + ")",
            "$b = [System.IO.File]::ReadAllBytes($env:PS_OUT)",
            '"bom=" + ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)',
            '"hex=" + (($b | ForEach-Object { $_.ToString("X2") }) -join "")',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_OUT": str(tmp_path / "out.txt")})
    assert code == 0, err
    assert "bom=False" in out
    assert "hex=312E342E300A" in out


def test_repo_version_files_have_no_bom():
    """正式 repo 的版本檔不得帶 UTF-8 BOM（舊版 client 會解析失敗）。"""
    for name in ("latest_version.txt", "latest_version_prerelease.txt"):
        raw = (REPO_ROOT / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), name + " 仍帶 UTF-8 BOM"
        assert raw.decode("utf-8").strip(), name + " 內容為空"


@requires_pwsh
@requires_ps51
def test_ps51_and_ps7_write_identical_bytes(tmp_path, ps_funcs):
    """Windows PowerShell 5.1 與 PowerShell 7 必須寫出完全相同的位元組。"""
    body = 'Write-Utf8NoBomText -Path $env:PS_OUT -Text ("1.4.0" + ' + LF + ")"
    out7 = tmp_path / "ps7.txt"
    out51 = tmp_path / "ps51.txt"
    code7, _, err7 = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_OUT": str(out7)})
    code51, _, err51 = run_ps(body, tmp_path, shell=POWERSHELL_51, env={"PS_FUNCS": str(ps_funcs), "PS_OUT": str(out51)})
    assert code7 == 0, err7
    assert code51 == 0, err51
    assert out7.read_bytes() == out51.read_bytes()
    assert out7.read_bytes() == b"1.4.0\n"


# ── 6. _parse_version 的 BOM 容錯 ──────────────────────────────────


def test_parse_version_tolerates_bom():
    assert _parse_version("\ufeff1.4.0") == (1, 4, 0, 1)
    assert _parse_version("\ufeffv1.4.0") == (1, 4, 0, 1)


def test_parse_version_keeps_existing_behaviour():
    assert _parse_version("1.4.0") == (1, 4, 0, 1)
    assert _parse_version("v1.4.0") == (1, 4, 0, 1)
    assert _parse_version("1.2.2-beta") == (1, 2, 2, 0)
    assert _parse_version("") == (0,)
    assert _parse_version("abc") == (0,)
    assert _parse_version("1.4") == (0,)
    assert _parse_version("1.4.0") > _parse_version("1.4.0-beta")


# ── 7. staging allowlist 靜態檢查 ──────────────────────────────────


def test_staging_allowlist_includes_uv_lock_and_pyproject():
    """uv.lock 受版本控制 → 必須列入 RequiredStagePaths。

    否則版本更新後的 lockfile 會殘留在工作區、與 release commit 不一致。
    """
    text = RELEASE_PS1.read_text(encoding="utf-8-sig")

    def _paths(block):
        code = "\n".join(ln for ln in block.splitlines() if not ln.strip().startswith("#"))
        return re.findall(r'"([^"]+)"', code)

    required = _paths(text.split("$script:RequiredStagePaths = @(")[1].split(")")[0])
    optional = _paths(text.split("$script:OptionalStagePaths = @(")[1].split(")")[0])
    assert "pyproject.toml" in required
    assert "uv.lock" in required
    assert "uv.lock" not in optional


# ── 8. 端到端：release.ps1 的中止行為（隔離 sandbox git repo）─────────

RELEASE_REQUIRED_STUBS = (
    "src/updater_core.py",
    "src/auto_update.py",
    "updater_main.py",
    "tools/build.py",
    "tools/make_delta.py",
    "scripts/requirements.txt",
    "latest_version.txt",
)


def make_release_sandbox(root):
    """建立可執行 release.ps1 的 sandbox git repo（所有必要路徑皆存在且已提交）。"""
    write_sandbox(root)
    for rel in RELEASE_REQUIRED_STUBS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# stub\n", encoding="utf-8")
    shutil.copy(RELEASE_PS1, root / "release.ps1")
    subprocess.run([REAL_GIT, "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run([REAL_GIT, "add", "-A"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(
        [REAL_GIT, "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-q", "-m", "init"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    return root


def write_git_shim(shim_dir):
    """建立攔截 git 呼叫的 shim（記錄到 GIT_SHIM_LOG，可用 GIT_SHIM_FAIL 讓指定子命令失敗）。"""
    shim_dir.mkdir(parents=True, exist_ok=True)
    (shim_dir / "git.cmd").write_text(
        '@echo off\r\necho %* >> "%GIT_SHIM_LOG%"\r\nif "%GIT_SHIM_FAIL%"=="%1" exit /b 1\r\n"' + REAL_GIT + '" %*\r\nexit /b %ERRORLEVEL%\r\n',
        encoding="ascii",
    )
    return shim_dir


def shim_verbs(log_path):
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return [ln.split()[0] for ln in text.splitlines() if ln.strip()]


def run_release(root, args, shim_dir=None, log_path=None, extra_env=None):
    env = dict(os.environ)
    if shim_dir is not None:
        env["PATH"] = str(shim_dir) + os.pathsep + env["PATH"]
        env["GIT_SHIM_LOG"] = str(log_path)
        env["GIT_SHIM_FAIL"] = ""
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})
    return subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(root / "release.ps1"), *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


@requires_pwsh
@requires_git
def test_release_rejects_invalid_version_without_writing(tmp_path):
    """無效版本字串必須在任何寫入 / staging / commit / tag / push 前中止。"""
    root = make_release_sandbox(tmp_path / "rel")
    before_version = (root / "src" / "_version.py").read_bytes()
    before_pyproject = (root / "pyproject.toml").read_bytes()
    log = tmp_path / "shim.log"
    proc = run_release(root, ["-Version", "abc"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=log)
    assert proc.returncode != 0
    assert "版本格式無效" in proc.stdout
    assert (root / "src" / "_version.py").read_bytes() == before_version
    assert (root / "pyproject.toml").read_bytes() == before_pyproject
    assert not any(v in ("add", "commit", "tag", "push") for v in shim_verbs(log))


@requires_pwsh
@requires_git
def test_consistency_gate_blocks_every_git_operation(tmp_path):
    """一致性閘門失敗時，git add / commit / tag / push 皆不得執行。"""
    root = make_release_sandbox(tmp_path / "rel")
    pp = root / "pyproject.toml"
    pp.write_text(pp.read_text(encoding="utf-8").replace('version = "1.4.0"', 'version = "9.9.9"', 1), encoding="utf-8")
    subprocess.run([REAL_GIT, "add", "-A"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(
        [REAL_GIT, "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-q", "-m", "drift"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    log = tmp_path / "shim.log"
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=log)
    assert proc.returncode != 0
    assert "一致性" in proc.stdout
    verbs = shim_verbs(log)
    assert not any(v in ("add", "commit", "tag", "push") for v in verbs), "閘門失敗時不得執行 git add/commit/tag/push：" + str(verbs)


@requires_pwsh
@requires_git
def test_consistent_release_reaches_staging(tmp_path):
    """版本一致時 -StageOnly 必須真的執行 staging（正面控制組）。"""
    root = make_release_sandbox(tmp_path / "rel")
    log = tmp_path / "shim.log"
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=log)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "staging 檢查完成" in proc.stdout
    assert "add" in shim_verbs(log)


@requires_pwsh
@requires_git
def test_release_without_version_does_not_rewrite_version_files(tmp_path):
    """不帶 -Version 時不得重寫版本檔案（mtime 不變）。"""
    root = make_release_sandbox(tmp_path / "rel")
    version_file = root / "src" / "_version.py"
    pyproject = root / "pyproject.toml"
    before = (version_file.stat().st_mtime_ns, pyproject.stat().st_mtime_ns)
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=tmp_path / "shim.log")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (version_file.stat().st_mtime_ns, pyproject.stat().st_mtime_ns) == before


# ── 9. Commitizen 設定與文件規範 ─────────────────────────────────


def test_commitizen_version_files_has_no_invalid_toml_path():
    """commitizen 的 version_files 是「行級 regex 比對」，不是 TOML 路徑語意。

    "pyproject.toml:project.version" 會被當成 regex 去逐行比對，永远匹配不到
    version 行 → 靜默無作用，且 cz bump --check-consistency 會直接 exit 17。
    因此 pyproject.toml 不得再帶這個條目。
    """
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("version_files = [")[1].split("]")[0]
    entries = re.findall(r'"([^"]+)"', block)
    assert "src/_version.py:__version__" in entries
    assert "pyproject.toml:project.version" not in entries
    for entry in entries:
        if ":" in entry:
            assert entry.split(":", 1)[1] == "__version__", "不得使用非 __version__ 的 pattern：" + entry


def test_agents_md_forbids_commitizen_release_commands():
    """AGENTS.md 不得指示用 cz bump / cz changelog（會改版本、commit、tag 或覆寫 CHANGELOG）。"""
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "禁止使用 `cz bump` 與 `cz changelog`" in text
    assert "cz changelog --dry-run" in text
    assert "只用於開發期產生 CHANGELOG 條目" not in text
    assert "commitizen 自動維護" not in text


def test_changelog_is_documented_as_manual():
    """文件索引不得宣稱 CHANGELOG 由 commitizen 自動維護。"""
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "CHANGELOG.md" in text
    assert "人工維護" in text


# ── 10. uv.lock 受版本控制 ───────────────────────────────────────


def test_gitignore_does_not_exclude_uv_lock():
    """.gitignore 不得再排除 uv.lock（它已是受追蹤的依賴鎖定檔）。"""
    lines = [ln.strip() for ln in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()]
    assert "/uv.lock" not in lines
    assert "uv.lock" not in lines


@requires_git
def test_git_does_not_ignore_uv_lock():
    proc = subprocess.run([REAL_GIT, "check-ignore", "-q", "--", "uv.lock"], cwd=str(REPO_ROOT), capture_output=True)
    assert proc.returncode != 0, "uv.lock 仍被 .gitignore 忽略"


def test_uv_lock_matches_project_version():
    """uv.lock 專案條目版本必須與 src/_version.py 一致。"""
    lock = REPO_ROOT / "uv.lock"
    assert lock.is_file(), "uv.lock 不存在"
    text = lock.read_text(encoding="utf-8")
    match = re.search(r'\[\[package\]\]\nname = "gametools-health-monitor"\nversion = "([^"]+)"', text)
    assert match, "uv.lock 找不到專案條目"
    version_py = (REPO_ROOT / "src" / "_version.py").read_text(encoding="utf-8")
    expected = re.search(r'__version__ = "([^"]+)"', version_py).group(1)
    assert match.group(1) == expected


@requires_git
def test_uv_lock_is_tracked_by_git():
    """uv.lock 必須受 Git 追蹤（已加入版本控制且未被 .gitignore 忽略）。"""
    proc = subprocess.run([REAL_GIT, "ls-files", "--error-unmatch", "--", "uv.lock"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, "uv.lock 未受 Git 追蹤"


def test_clean_checkout_can_sync_locked(tmp_path):
    """乾淨環境（只有受追蹤的 pyproject.toml + uv.lock）必須能 uv sync --locked。"""
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv 不可用")
    clean = tmp_path / "clean"
    clean.mkdir()
    shutil.copy(REPO_ROOT / "pyproject.toml", clean / "pyproject.toml")
    shutil.copy(REPO_ROOT / "uv.lock", clean / "uv.lock")
    proc = subprocess.run([uv, "sync", "--locked", "--dry-run"], cwd=str(clean), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ── 11. release.ps1 的 shim（隔離測試用）─────────────────────────

UV_SHIM = (
    "@echo off\r\n"
    + 'echo %* >> "%UV_SHIM_LOG%"\r\n'
    + 'if "%UV_SHIM_MODE%"=="create_lock" echo # fake lock > uv.lock\r\n'
    + 'if "%UV_SHIM_MODE%"=="ok_lock" copy /Y "%UV_SHIM_LOCK_SRC%" uv.lock >nul\r\n'
    + "exit /b %UV_SHIM_EXIT%\r\n"
)

GH_SHIM = "@echo off\r\n" + 'echo %* >> "%GH_SHIM_LOG%"\r\n' + "exit /b %GH_SHIM_EXIT%\r\n"

VPK_SHIM = "@echo off\r\n" + 'echo %* >> "%VPK_SHIM_LOG%"\r\n' + "exit /b %VPK_SHIM_EXIT%\r\n"


def write_cmd_shim(shim_dir, name, body):
    shim_dir.mkdir(parents=True, exist_ok=True)
    (shim_dir / name).write_text(body, encoding="ascii")
    return shim_dir


def release_env(tmp_path, **extra):
    env = {"TEMP": str(tmp_path), "TMP": str(tmp_path)}
    env.update({k: str(v) for k, v in extra.items()})
    return env


def report_path_from(stdout):
    match = re.search(r"失敗報告：(\S+)", stdout)
    return match.group(1) if match else None


# ── 12. 版本同步失敗的回滾 ───────────────────────────────────────


@requires_pwsh
@requires_git
def test_uv_lock_failure_rolls_back_every_file(tmp_path):
    """uv lock 失敗 → _version.py / pyproject.toml / uv.lock 全部還原為原始位元組。"""
    root = make_release_sandbox(tmp_path / "rel")
    paths = ("src/_version.py", "pyproject.toml", "uv.lock")
    before = tuple((root / p).read_bytes() for p in paths)

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
    proc = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=tmp_path / "uv.log", UV_SHIM_EXIT=1, UV_SHIM_MODE=""),
    )
    assert proc.returncode != 0
    assert "版本同步失敗" in proc.stdout
    assert tuple((root / p).read_bytes() for p in paths) == before, "失敗後必須回到執行前的位元組"


@requires_pwsh
@requires_git
def test_rollback_removes_newly_created_uv_lock(tmp_path):
    """原本沒有 uv.lock 時，失敗後必須維持「不存在」（不得留下半成品）。"""
    root = make_release_sandbox(tmp_path / "rel")
    (root / "uv.lock").unlink()
    before_version = (root / "src" / "_version.py").read_bytes()
    before_pyproject = (root / "pyproject.toml").read_bytes()

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
    proc = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=tmp_path / "uv.log", UV_SHIM_EXIT=1, UV_SHIM_MODE="create_lock"),
    )
    assert proc.returncode != 0
    assert not (root / "uv.lock").exists(), "本次產生的 uv.lock 必須被移除"
    assert (root / "src" / "_version.py").read_bytes() == before_version
    assert (root / "pyproject.toml").read_bytes() == before_pyproject


@requires_pwsh
def test_partial_write_failure_rollback_restores_bytes(tmp_path, ps_funcs):
    """第一個版本檔寫入成功、第二個失敗 → 所有原始位元組（含 BOM / CRLF）完整還原。"""
    root = tmp_path / "enc"
    (root / "src").mkdir(parents=True)
    version_file = root / "src" / "_version.py"
    pyproject = root / "pyproject.toml"
    uv_lock = root / "uv.lock"
    version_file.write_bytes(b'\xef\xbb\xbf__version__ = "1.4.0"\r\n')
    pyproject.write_bytes(b'[project]\r\nversion = "1.4.0"\r\n\r\n[tool.commitizen]\r\nversion = "1.4.0"\r\n')
    uv_lock.write_bytes(b'[[package]]\r\nname = "gametools-health-monitor"\r\nversion = "1.4.0"\r\n')
    before = (version_file.read_bytes(), pyproject.read_bytes(), uv_lock.read_bytes())

    body = "\n".join(
        [
            "$b = @(",
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "src\\_version.py"))',
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "pyproject.toml"))',
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "uv.lock"))',
            ")",
            'Set-ItemProperty -Path (Join-Path $env:PS_SANDBOX "pyproject.toml") -Name IsReadOnly -Value $true',
            "try {",
            '    Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.5.0"',
            '    "NO_ERROR"',
            "} catch {",
            '    "SYNC_FAILED"',
            "}",
            '"first_write_changed=" + (-not (Test-FileBackupRestored -Backup $b[0]))',
            'Set-ItemProperty -Path (Join-Path $env:PS_SANDBOX "pyproject.toml") -Name IsReadOnly -Value $false',
            "$r = Restore-FileBackup -Backups $b",
            '"restore_ok=" + $r.Ok',
            '"restored_count=" + (@($b | Where-Object { Test-FileBackupRestored -Backup $_ }).Count)',
        ]
    )
    code, out, err = run_ps(body, tmp_path, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(root)})
    assert code == 0, err
    assert "SYNC_FAILED" in out
    assert "first_write_changed=True" in out
    assert "restore_ok=True" in out
    assert "restored_count=3" in out
    assert (version_file.read_bytes(), pyproject.read_bytes(), uv_lock.read_bytes()) == before


@requires_pwsh
@requires_git
def test_rollback_failure_is_reported_and_blocks_staging(tmp_path):
    """回滾本身失敗 → 明確列出未還原檔案、寫出失敗報告，且不得進入 staging。"""
    root = make_release_sandbox(tmp_path / "rel")
    pyproject = root / "pyproject.toml"
    before_version = (root / "src" / "_version.py").read_bytes()
    os.chmod(pyproject, 0o444)
    try:
        shim_dir = write_git_shim(tmp_path / "shim")
        write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
        proc = run_release(
            root,
            ["-Version", "1.5.0"],
            shim_dir=shim_dir,
            log_path=tmp_path / "shim.log",
            extra_env=release_env(tmp_path, UV_SHIM_LOG=tmp_path / "uv.log", UV_SHIM_EXIT=1, UV_SHIM_MODE=""),
        )
    finally:
        os.chmod(pyproject, 0o666)

    assert proc.returncode != 0
    assert "回滾未完全成功" in proc.stdout
    assert "pyproject.toml" in proc.stdout
    report = report_path_from(proc.stdout)
    assert report, "必須印出失敗報告路徑"
    assert Path(report).is_file()
    content = Path(report).read_text(encoding="utf-8")
    assert "pyproject.toml" in content
    assert "還原失敗檔案" in content
    assert (root / "src" / "_version.py").read_bytes() == before_version
    verbs = shim_verbs(tmp_path / "shim.log")
    assert not any(v in ("add", "commit", "tag", "push") for v in verbs), "回滾失敗時不得進入 staging：" + str(verbs)


@requires_pwsh
@requires_git
def test_consistency_gate_failure_rolls_back(tmp_path):
    """一致性閘門失敗（lockfile 過期）→ 完整還原，且不進入 staging。"""
    root = make_release_sandbox(tmp_path / "rel")
    paths = ("src/_version.py", "pyproject.toml", "uv.lock")
    before = tuple((root / p).read_bytes() for p in paths)

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
    proc = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=tmp_path / "uv.log", UV_SHIM_EXIT=0, UV_SHIM_MODE=""),
    )
    assert proc.returncode != 0
    assert "一致性" in proc.stdout
    assert tuple((root / p).read_bytes() for p in paths) == before
    verbs = shim_verbs(tmp_path / "shim.log")
    assert not any(v in ("add", "commit", "tag", "push") for v in verbs)


# ── 13. 同版本重跑必須重新同步與更新 lockfile ───────────────────


@requires_pwsh
@requires_git
def test_same_version_rerun_still_updates_lockfile(tmp_path):
    """版本欄位已是目標版本時，仍必須執行 uv lock（舊版會跳過 → 閘門永久失敗）。"""
    root = make_release_sandbox(tmp_path / "rel")
    (root / "src" / "_version.py").write_text('__version__ = "1.5.0"\n', encoding="utf-8")
    pyproject = root / "pyproject.toml"
    pyproject.write_text(pyproject.read_text(encoding="utf-8").replace('version = "1.4.0"', 'version = "1.5.0"'), encoding="utf-8")

    lock_src = tmp_path / "lock_150.txt"
    lock_src.write_text('[[package]]\nname = "gametools-health-monitor"\nversion = "1.5.0"\nsource = { virtual = "." }\n', encoding="utf-8")

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
    uv_log = tmp_path / "uv.log"
    proc = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=uv_log, UV_SHIM_EXIT=0, UV_SHIM_MODE="ok_lock", UV_SHIM_LOCK_SRC=lock_src),
    )
    calls = [ln.strip() for ln in uv_log.read_text(encoding="utf-8").splitlines() if ln.strip()] if uv_log.exists() else []
    assert any(c.startswith("lock") for c in calls), "同版本重跑仍必須執行 uv lock：" + str(calls)
    assert "版本一致性檢查通過" in proc.stdout
    assert 'version = "1.5.0"' in (root / "uv.lock").read_text(encoding="utf-8")


@requires_pwsh
@requires_git
def test_rerun_after_failed_sync_recovers(tmp_path):
    """第一次同步後 lock 失敗 → 第二次以相同 -Version 必須能重新同步並更新 lockfile。"""
    root = make_release_sandbox(tmp_path / "rel")
    lock_src = tmp_path / "lock_150.txt"
    lock_src.write_text('[[package]]\nname = "gametools-health-monitor"\nversion = "1.5.0"\nsource = { virtual = "." }\n', encoding="utf-8")

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "uv.cmd", UV_SHIM)
    uv_log = tmp_path / "uv.log"

    proc1 = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=uv_log, UV_SHIM_EXIT=1, UV_SHIM_MODE=""),
    )
    assert proc1.returncode != 0
    assert '__version__ = "1.4.0"' in (root / "src" / "_version.py").read_text(encoding="utf-8"), "第一次失敗後必須回滾"

    proc2 = run_release(
        root,
        ["-Version", "1.5.0"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, UV_SHIM_LOG=uv_log, UV_SHIM_EXIT=0, UV_SHIM_MODE="ok_lock", UV_SHIM_LOCK_SRC=lock_src),
    )
    assert "版本一致性檢查通過" in proc2.stdout, proc2.stdout
    assert '__version__ = "1.5.0"' in (root / "src" / "_version.py").read_text(encoding="utf-8")
    assert 'version = "1.5.0"' in (root / "uv.lock").read_text(encoding="utf-8")


@requires_pwsh
@requires_git
def test_release_without_version_does_not_touch_uv_lock(tmp_path):
    """不帶 -Version 時不得重寫版本欄位或 lockfile。"""
    root = make_release_sandbox(tmp_path / "rel")
    version_file = root / "src" / "_version.py"
    pyproject = root / "pyproject.toml"
    uv_lock = root / "uv.lock"
    before = (version_file.stat().st_mtime_ns, pyproject.stat().st_mtime_ns, uv_lock.stat().st_mtime_ns)
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=tmp_path / "shim.log")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (version_file.stat().st_mtime_ns, pyproject.stat().st_mtime_ns, uv_lock.stat().st_mtime_ns) == before


# ── 14. TestRepo 自動還原 ───────────────────────────────────────


def prepare_testrepo_assets(root):
    """TestRepo 模式不清 dist/vpk，先放好資產讓流程走到 gh release create。"""
    vpk_dir = root / "dist" / "vpk"
    vpk_dir.mkdir(parents=True, exist_ok=True)
    (vpk_dir / "Sid.GameToolsHealthMonitor.1.2.2-test.1-full.nupkg").write_bytes(b"x")
    (vpk_dir / "Sid.GameToolsHealthMonitor-Setup.exe").write_bytes(b"x")
    (vpk_dir / "releases.win.json").write_text("{}", encoding="utf-8")
    (vpk_dir / "RELEASES").write_text("", encoding="utf-8")
    (vpk_dir / "assets.win.json").write_text("{}", encoding="utf-8")
    return vpk_dir


def run_testrepo(root, tmp_path, *, build_exit=0, gh_exit=0, vpk_exit=0, read_only_after_build=False):
    build = root / "tools" / "build.py"
    if read_only_after_build:
        build.write_text(
            "import os, stat, sys\nos.chmod(os.path.join('src', '_version.py'), stat.S_IREAD)\nsys.exit(%d)\n" % build_exit,
            encoding="utf-8",
        )
    else:
        build.write_text("import sys\nsys.exit(%d)\n" % build_exit, encoding="utf-8")

    shim_dir = write_git_shim(tmp_path / "shim")
    write_cmd_shim(shim_dir, "gh.cmd", GH_SHIM)
    write_cmd_shim(shim_dir, "vpk.cmd", VPK_SHIM)
    proc = run_release(
        root,
        ["-TestRepo", "-Version", "1.2.2-test.1"],
        shim_dir=shim_dir,
        log_path=tmp_path / "shim.log",
        extra_env=release_env(tmp_path, GH_SHIM_LOG=tmp_path / "gh.log", GH_SHIM_EXIT=gh_exit, VPK_SHIM_LOG=tmp_path / "vpk.log", VPK_SHIM_EXIT=vpk_exit),
    )
    version_file = root / "src" / "_version.py"
    if read_only_after_build:
        try:
            os.chmod(version_file, 0o666)
        except OSError:
            pass
    return proc


@requires_pwsh
@requires_git
def test_testrepo_restores_version_file_on_success(tmp_path):
    """測試倉正常完成後，_version.py 必須逐位元組還原。"""
    root = make_release_sandbox(tmp_path / "rel")
    prepare_testrepo_assets(root)
    version_file = root / "src" / "_version.py"
    before = version_file.read_bytes()

    proc = run_testrepo(root, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert version_file.read_bytes() == before
    assert "已還原為執行前狀態" in proc.stdout


@requires_pwsh
@requires_git
def test_testrepo_restores_version_file_after_build_failure(tmp_path):
    """build 失敗後仍必須還原 _version.py。"""
    root = make_release_sandbox(tmp_path / "rel")
    prepare_testrepo_assets(root)
    version_file = root / "src" / "_version.py"
    before = version_file.read_bytes()

    proc = run_testrepo(root, tmp_path, build_exit=3)
    assert proc.returncode != 0
    assert version_file.read_bytes() == before


@requires_pwsh
@requires_git
def test_testrepo_restores_version_file_after_pack_failure(tmp_path):
    """Velopack pack 失敗後仍必須還原 _version.py。"""
    root = make_release_sandbox(tmp_path / "rel")
    prepare_testrepo_assets(root)
    version_file = root / "src" / "_version.py"
    before = version_file.read_bytes()

    proc = run_testrepo(root, tmp_path, vpk_exit=1)
    assert proc.returncode != 0
    assert version_file.read_bytes() == before


@requires_pwsh
@requires_git
def test_testrepo_restores_version_file_after_gh_failure(tmp_path):
    """gh release create 失敗（流程末端）後仍必須還原 _version.py。"""
    root = make_release_sandbox(tmp_path / "rel")
    prepare_testrepo_assets(root)
    version_file = root / "src" / "_version.py"
    before = version_file.read_bytes()

    proc = run_testrepo(root, tmp_path, gh_exit=1)
    assert proc.returncode != 0
    assert version_file.read_bytes() == before


@requires_pwsh
@requires_git
def test_testrepo_restore_failure_ends_with_error(tmp_path):
    """還原失敗 → 必須以明確錯誤結束，不得回報測試倉發布成功。"""
    root = make_release_sandbox(tmp_path / "rel")
    prepare_testrepo_assets(root)

    proc = run_testrepo(root, tmp_path, read_only_after_build=True)
    assert proc.returncode != 0
    assert "還原失敗" in proc.stdout
    report = report_path_from(proc.stdout)
    assert report and Path(report).is_file()


# ── 15. staging safety 仍有效 ───────────────────────────────────


def _allowlist_paths(text):
    def _paths(block):
        code = "\n".join(ln for ln in block.splitlines() if not ln.strip().startswith("#"))
        return re.findall(r'"([^"]+)"', code)

    required = _paths(text.split("$script:RequiredStagePaths = @(")[1].split(")")[0])
    optional = _paths(text.split("$script:OptionalStagePaths = @(")[1].split(")")[0])
    return required, optional


@requires_pwsh
@requires_git
def test_stageonly_stages_exactly_the_allowlist(tmp_path):
    """加入 uv.lock 後仍只能 stage allowlist 中明確列出的檔案。"""
    root = make_release_sandbox(tmp_path / "rel")
    # 讓 uv.lock 有實質變更，否則 git add 不會產生 staged 項目
    lock = root / "uv.lock"
    lock.write_text(lock.read_text(encoding="utf-8") + "# touched by staging test\n", encoding="utf-8")
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=tmp_path / "shim.log")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = subprocess.run([REAL_GIT, "diff", "--cached", "--name-only"], cwd=str(root), capture_output=True, text=True, encoding="utf-8").stdout.split()
    required, optional = _allowlist_paths(RELEASE_PS1.read_text(encoding="utf-8-sig"))
    allowed = set(required) | set(optional)
    assert "uv.lock" in staged, "uv.lock 必須被 stage"
    for name in staged:
        assert name in allowed, "不得 stage allowlist 以外的檔案：" + name


@requires_pwsh
@requires_git
def test_dirty_path_guard_still_blocks_release(tmp_path):
    """dirty-path guard 仍然有效：非發布範圍的未提交修改必須擋下。"""
    root = make_release_sandbox(tmp_path / "rel")
    (root / "unrelated.txt").write_text("scratch\n", encoding="utf-8")
    log = tmp_path / "shim.log"
    proc = run_release(root, ["-StageOnly"], shim_dir=write_git_shim(tmp_path / "shim"), log_path=log)
    assert proc.returncode != 0
    assert "未提交的開發修改" in proc.stdout
    assert not any(v in ("add", "commit", "tag", "push") for v in shim_verbs(log))


# ── 16. PowerShell 5.1 / 7 的關鍵流程行為一致 ────────────────────


@requires_pwsh
@requires_ps51
def test_ps51_and_ps7_backup_restore_produce_identical_bytes(tmp_path, ps_funcs):
    """關鍵回滾流程在 Windows PowerShell 5.1 與 PowerShell 7 必須行為一致。

    這是行為測試（實際執行 release.ps1 的真實函式），不是 AST 字串檢查。
    """

    def _make(root):
        (root / "src").mkdir(parents=True)
        (root / "src" / "_version.py").write_bytes(b'\xef\xbb\xbf__version__ = "1.4.0"\r\n')
        (root / "pyproject.toml").write_bytes(b'[project]\nversion = "1.4.0"\n\n[tool.commitizen]\nversion = "1.4.0"\n')
        (root / "uv.lock").write_bytes(b'[[package]]\nname = "gametools-health-monitor"\nversion = "1.4.0"\n')

    body = "\n".join(
        [
            "$b = @(",
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "src\\_version.py"))',
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "pyproject.toml"))',
            '  (New-FileBackup -Path (Join-Path $env:PS_SANDBOX "uv.lock"))',
            ")",
            'Sync-VersionFields -RepoRoot $env:PS_SANDBOX -NewVersion "1.5.0"',
            "$r = Restore-FileBackup -Backups $b",
            '"restore_ok=" + $r.Ok',
            '"restored_count=" + (@($b | Where-Object { Test-FileBackupRestored -Backup $_ }).Count)',
        ]
    )

    results = []
    for index, shell in enumerate((PWSH, POWERSHELL_51)):
        root = tmp_path / ("shell" + str(index))
        _make(root)
        code, out, err = run_ps(body, tmp_path, shell=shell, env={"PS_FUNCS": str(ps_funcs), "PS_SANDBOX": str(root)})
        assert code == 0, err
        assert "restore_ok=True" in out
        assert "restored_count=3" in out
        results.append((root / "src" / "_version.py").read_bytes() + (root / "pyproject.toml").read_bytes() + (root / "uv.lock").read_bytes())

    assert results[0] == results[1], "PS 5.1 與 PS 7 的回滾結果位元組不同"
    assert results[0].startswith(b"\xef\xbb\xbf"), "BOM 必須被保留"
    assert b"1.4.0" in results[0] and b"1.5.0" not in results[0], "必須還原為原始版本"


@requires_pwsh
@requires_ps51
@requires_git
def test_release_stageonly_works_on_windows_powershell_51(tmp_path):
    """release.ps1 的 staging 自我檢查在 Windows PowerShell 5.1 也必須可用。"""
    root = make_release_sandbox(tmp_path / "rel")
    env = dict(os.environ)
    env["PATH"] = str(write_git_shim(tmp_path / "shim")) + os.pathsep + env["PATH"]
    env["GIT_SHIM_LOG"] = str(tmp_path / "shim.log")
    env["GIT_SHIM_FAIL"] = ""
    proc = subprocess.run(
        [POWERSHELL_51, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(root / "release.ps1"), "-StageOnly"],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "staging 檢查完成" in proc.stdout
    assert "add" in shim_verbs(tmp_path / "shim.log")


# ── 18. Windows 批次腳本必須使用 CRLF ───────────────────────────


def test_batch_scripts_use_crlf_line_endings():
    """cmd.exe 解析 LF-only 的 .bat 會錯亂（括號區塊與 goto 失效，錯誤訊息被吞掉）。"""
    for name in ("scripts/install_dependencies.bat", "scripts/build_exe.bat", "scripts/cleanup.bat", "Run.bat"):
        raw = (REPO_ROOT / name).read_bytes()
        assert b"\r\n" in raw, name + " 不是 CRLF 換行"
        assert raw.replace(b"\r\n", b"").count(b"\n") == 0, name + " 含有裸 LF"


def test_install_script_uses_goto_labels_and_call():
    """安裝腳本改用 goto 標籤與 call，避免 cmd.exe 的括號區塊解析陷阱。

    1. if 區塊內的 echo 若含 ( ) 或 ! ，cmd.exe 會誤判區塊邊界（實測會讓
       "uv 已安裝" 被誤判成 "找不到 uv"，且錯誤訊息整行被吞掉）。
    2. 以批次檔形式的 uv 未加 call 時，會奪走整個腳本控制權（無訊息直接結束）。
    """
    text = (REPO_ROOT / "scripts" / "install_dependencies.bat").read_text(encoding="utf-8")
    assert "if %errorlevel%" not in text, "不得使用 %errorlevel%（區塊解析脆弱）"
    assert "goto :" in text, "錯誤分支必須使用 goto 標籤"
    assert "call uv sync --locked" in text, "批次形式的 uv 必須以 call 呼叫"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("echo"):
            assert "(" not in stripped, "echo 行不得含裸括號：" + stripped
            assert "!" not in stripped, "echo 行不得含驚嘆號：" + stripped
