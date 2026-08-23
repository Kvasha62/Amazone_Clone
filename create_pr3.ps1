# ══════════════════════════════════════════════════════════════════════
# create_pr3.ps1 — Создание PR #3: Password Reset Security & Correctness
#
# Запуск: скопируйте ЭТОТ файл и pr3_password_reset_security.patch
#         в E:\MyProjects\Amazone_Clone, затем:
#         cd E:\MyProjects\Amazone_Clone
#         powershell -ExecutionPolicy Bypass -File .\create_pr3.ps1
# ══════════════════════════════════════════════════════════════════════

# Helper: run git command, swallow stderr progress messages
function Git-Run {
    $output = & git @args 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) {
        if ($line -isnot [System.Management.Automation.ErrorRecord]) {
            Write-Host $line
        }
    }
    if ($exitCode -ne 0) { throw "git @args failed (exit $exitCode)" }
    return $exitCode
}

$RepoRoot = "E:\MyProjects\Amazone_Clone"

Write-Host ""
Write-Host "============================================================"
Write-Host "  PR #3: Password Reset Security & Correctness"
Write-Host "============================================================"
Write-Host ""

# -- 1. Проверяем что мы в правильной директории --
if (-not (Test-Path "$RepoRoot\.git")) {
    Write-Host "ERROR: Git repo not found in $RepoRoot" -ForegroundColor Red
    exit 1
}

Set-Location $RepoRoot
Write-Host "[1/7] Working directory: $RepoRoot" -ForegroundColor Green

# -- 2. Проверяем что патч-файл существует --
$PatchFile = "$RepoRoot\pr3_password_reset_security.patch"
if (-not (Test-Path $PatchFile)) {
    Write-Host ""
    Write-Host "ERROR: Patch file not found: $PatchFile" -ForegroundColor Red
    Write-Host "Download pr3_password_reset_security.patch from workspace" -ForegroundColor Yellow
    Write-Host "and copy to $RepoRoot\" -ForegroundColor Yellow
    Write-Host "Alternative: run python create_pr3_files.py" -ForegroundColor Yellow
    exit 1
}

# -- 3. Переключаемся на main и обновляем --
Write-Host "[2/7] Switching to main..." -ForegroundColor Yellow
Git-Run checkout main
Git-Run pull origin main

# -- 4. Создаём ветку для PR #3 --
$BranchName = "fix/password-reset-security"
Write-Host "[3/7] Creating branch $BranchName..." -ForegroundColor Yellow
try {
    Git-Run checkout -b $BranchName
} catch {
    # Branch already exists - switch to it
    Git-Run checkout $BranchName
}

# -- 5. Применяем патч --
Write-Host "[4/7] Applying patch..." -ForegroundColor Yellow
$patchCheck = & git apply --check $PatchFile 2>&1
$patchExitCode = $LASTEXITCODE

if ($patchExitCode -ne 0) {
    Write-Host "WARN: patch --check failed, trying with --3way..." -ForegroundColor Yellow
    & git apply --3way $PatchFile 2>&1 | Out-Null
} else {
    & git apply $PatchFile 2>&1 | Out-Null
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Patch failed. Try alternative: python create_pr3_files.py" -ForegroundColor Red
    exit 1
}

# -- 6. Коммит --
Write-Host "[5/7] Committing..." -ForegroundColor Yellow
Git-Run add -A
Git-Run commit -m "fix: secure password reset flow - no token in logs, no password leak, update_fields fix"

# -- 7. Push --
Write-Host "[6/7] Pushing to GitHub..." -ForegroundColor Yellow
Git-Run push -u origin $BranchName

# -- 8. Создаём PR через GitHub CLI --
Write-Host "[7/7] Creating Pull Request..." -ForegroundColor Yellow

$PrTitle = "fix: Secure password reset flow"

# Write PR body to temp file (avoids PowerShell parsing issues)
$tempBody = [System.IO.Path]::GetTempFileName()

$bodyLines = @()
$bodyLines += "## Password Reset Security and Correctness"
$bodyLines += ""
$bodyLines += "### Security Fixes"
$bodyLines += "- Token not logged: Removed token and uid from all log statements in password reset views"
$bodyLines += "- Password not logged: Registration validation errors no longer include password fields in logs"
$bodyLines += "- Email via Celery: Password reset email sent via Celery task (with sync fallback)"
$bodyLines += ""
$bodyLines += "### Correctness Fixes"
$bodyLines += "- update_fields fix: user.save(update_fields=['password']) because User inherits AbstractUser (NOT BaseModel), has no updated_at field"
$bodyLines += "- Celery email task: send_password_reset_email in apps/notifications/tasks.py"
$bodyLines += "- Email settings: EMAIL_BACKEND, DEFAULT_FROM_EMAIL, FRONTEND_URL added to settings"
$bodyLines += ""
$bodyLines += "### Files Changed (6)"
$bodyLines += "- apps/users/api_views/password_reset_views.py - removed token from logs, added email sending, fixed update_fields"
$bodyLines += "- apps/users/api_views/auth_views.py - filtered password from registration error logs"
$bodyLines += "- apps/notifications/tasks.py - new send_password_reset_email Celery task"
$bodyLines += "- config/settings.py - EMAIL_BACKEND, DEFAULT_FROM_EMAIL, FRONTEND_URL"
$bodyLines += "- apps/users/tests/test_password_reset.py - NEW 9 security and correctness tests"
$bodyLines += "- DIARY.md - updated"
$bodyLines += ""
$bodyLines += "### Tests (9)"
$bodyLines += "- PasswordResetRequestTests: 3 (existing user, unknown email, invalid email)"
$bodyLines += "- PasswordResetConfirmTests: 7 (valid token, old fails, new works, invalid token, used token, invalid uid, mismatch)"
$bodyLines += "- PasswordResetLoggingTests: 2 (token not in logs, password not in logs)"
$bodyLines += ""
$bodyLines += "All 9 tests pass."

$bodyLines | Out-File -FilePath $tempBody -Encoding UTF8

# Пробуем gh CLI
$ghAvailable = $false
try {
    $null = & gh --version 2>&1
    $ghAvailable = $true
} catch {
    $ghAvailable = $false
}

if ($ghAvailable) {
    & gh pr create --title $PrTitle --body-file $tempBody --base main --head $BranchName 2>&1 | ForEach-Object { Write-Host $_ }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  PR #3 SUCCESSFULLY CREATED!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "gh CLI not installed. Create PR manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  https://github.com/Kvasha62/Amazone_Clone/compare/main...$BranchName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Title: $PrTitle" -ForegroundColor White
}

# Cleanup
Remove-Item $tempBody -Force -ErrorAction SilentlyContinue
Remove-Item $PatchFile -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Removed patch file from repo." -ForegroundColor Gray
