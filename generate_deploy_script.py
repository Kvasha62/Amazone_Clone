#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор deploy_all_v3.ps1.
"""

import os
from pathlib import Path

WORKSPACE = Path("/home/user")
FRONTEND_ROOT = WORKSPACE / "frontend"
OUTPUT_SCRIPT = WORKSPACE / "deploy_all_v3.ps1"

BE_TARGET = "I:\\NewPythonProjects\\Amazone_Clone"
FE_TARGET = "I:\\NewPythonProjects\\frontend"

SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules",
    ".cache", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "media", "staticfiles", ".arena",
}

SKIP_FILES = {
    "db.sqlite3", "db.sqlite3-journal",
    "deploy_all.ps1", "deploy_all_v2.ps1", "deploy_all_v3.ps1",
    "deploy_backend_password_reset_views.py",
    "deploy_backend_product_brief_views.py",
    "deploy_frontend_src_CheckoutPage.tsx",
    "deploy_frontend_src_ErrorBoundary.tsx",
    "deploy_frontend_src_ForgotPasswordPage.tsx",
    "deploy_frontend_src_Header.tsx",
    "deploy_frontend_src_HomePage.tsx",
    "deploy_frontend_src_NotificationPage.tsx",
    "deploy_frontend_src_OrderDetailPage.tsx",
    "deploy_frontend_src_OrderListPage.tsx",
    "deploy_frontend_src_ProfilePage.tsx",
    "deploy_frontend_src_Skeleton.tsx",
    "deploy_frontend_src_Toast.tsx",
    "deploy_frontend_src_api_notifications.ts",
    "deploy_frontend_src_notificationStore.ts",
    "deploy_populate_admin.py",
    "deploy_populate_full.py",
    "fix_addresses.ps1",
    "generate_pdf.py",
    "test_register.py",
    "orders_serializers_fix.py",
    "frontend-router.tsx",
    "generate_deploy_script.py",
    "BACKEND_REVIEW_ANALYSIS.md",
    "COMPATIBILITY_REPORT.md",
    "POPULATE_ADMIN_FIX.md",
    "REACT_READINESS_REPORT.md",
    "WORKSPACE_VS_REPO_ANALYSIS.md",
    "API_REFERENCE.md",
    "SETUP_GUIDE.md",
    "TEXTBOOK.md",
}

SKIP_EXTENSIONS = {".pdf", ".pyc", ".pyo"}


def collect_files(root, exclude_prefix=None):
    """Collect all text files under root, returning [(relative_path, absolute_path)]."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel_dir = os.path.relpath(dirpath, root)

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root)

            # Skip by filename
            if fname in SKIP_FILES:
                continue
            # Skip .env (but not .env.example)
            if fname == ".env":
                continue
            # Skip by extension
            if os.path.splitext(fname)[1].lower() in SKIP_EXTENSIONS:
                continue
            # Skip frontend/ prefix for backend collection
            if exclude_prefix and rel.startswith(exclude_prefix):
                continue

            files.append((rel, fpath))

    return files


def main():
    print("=== Generating deploy_all_v3.ps1 ===")

    # Collect files
    backend_files = collect_files(WORKSPACE, exclude_prefix="frontend")
    frontend_files = collect_files(FRONTEND_ROOT)

    print(f"Backend files: {len(backend_files)}")
    print(f"Frontend files: {len(frontend_files)}")

    # Read all files and prepare blocks
    all_blocks = []
    counter = 0
    be_count = 0
    fe_count = 0

    # Backend files
    for rel, abspath in backend_files:
        try:
            content = Path(abspath).read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            print(f"  SKIP (binary/error): {rel}")
            continue

        # Convert rel path to Windows backslashes
        target = BE_TARGET + "\\" + rel.replace("/", "\\")
        var_name = f"f{counter:04d}"
        all_blocks.append(("be", var_name, content, target))
        counter += 1
        be_count += 1

    # Frontend files
    for rel, abspath in frontend_files:
        try:
            content = Path(abspath).read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            print(f"  SKIP (binary/error): {rel}")
            continue

        target = FE_TARGET + "\\" + rel.replace("/", "\\")
        var_name = f"f{counter:04d}"
        all_blocks.append(("fe", var_name, content, target))
        counter += 1
        fe_count += 1

    print(f"Total files to write: {len(all_blocks)}")

    # Generate PowerShell script
    lines = []

    # Header
    lines.append("# " + "=" * 69)
    lines.append("# deploy_all_v3.ps1 - Full repository deployment")
    lines.append("# AUTO-GENERATED - do not edit manually!")
    lines.append("# " + "=" * 69)
    lines.append("")
    lines.append('$ErrorActionPreference = "Stop"')
    lines.append("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8")
    lines.append("")
    lines.append('Write-Host ""')
    lines.append('Write-Host "  Amazone Clone - Deploy v3 (Auto-generated)" -ForegroundColor Cyan')
    lines.append('Write-Host ""')
    lines.append("")
    lines.append("# -- Create directories --")
    lines.append(f'$backendRoot = "{BE_TARGET}"')
    lines.append(f'$frontendRoot = "{FE_TARGET}"')
    lines.append("")
    lines.append("if (-not (Test-Path $backendRoot)) { New-Item -ItemType Directory -Path $backendRoot -Force | Out-Null }")
    lines.append("if (-not (Test-Path $frontendRoot)) { New-Item -ItemType Directory -Path $frontendRoot -Force | Out-Null }")
    lines.append("")
    lines.append('Write-Host "Writing backend files..." -ForegroundColor Yellow')
    lines.append("")

    # Write backend file blocks
    for kind, var_name, content, target in all_blocks:
        if kind == "fe":
            # Switch to frontend section
            lines.append("")
            lines.append('Write-Host ""')
            lines.append(f'Write-Host "  Backend: {be_count} files written" -ForegroundColor Green')
            lines.append('Write-Host "Writing frontend files..." -ForegroundColor Yellow')
            lines.append("")

        # Generate file block
        lines.append(f"$filePath = \"{target}\"")
        lines.append("$dir = Split-Path -Parent $filePath")
        lines.append("if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }")
        lines.append(f"${var_name} = @'")
        lines.append(content)
        lines.append("'@")
        lines.append("Set-Content -Path $filePath -Value $f" + var_name[1:] + " -Encoding UTF8NoBOM -Force")
        # Only add Write-Host progress every 50 files to reduce output
        lines.append("")

    # Git section
    lines.append("")
    lines.append(f'Write-Host "  Frontend: {fe_count} files written" -ForegroundColor Green')
    lines.append("")
    lines.append("# " + "=" * 69)
    lines.append("# Git init + commit")
    lines.append("# " + "=" * 69)
    lines.append("")
    lines.append("Push-Location $backendRoot")
    lines.append("")
    lines.append("if (-not (Test-Path '.git')) {")
    lines.append("    git init")
    lines.append("    git branch -m main")
    lines.append('    Write-Host "  git init + branch main" -ForegroundColor Green')
    lines.append("} else {")
    lines.append('    Write-Host "  git already initialized" -ForegroundColor Green')
    lines.append("}")
    lines.append("")
    lines.append("$currentUser = git config user.name 2>$null")
    lines.append("if (-not $currentUser) {")
    lines.append('    git config user.name "Oleg Kvashin"')
    lines.append('    git config user.email "kvasha62@users.noreply.github.com"')
    lines.append('    Write-Host "  git config user" -ForegroundColor Green')
    lines.append("}")
    lines.append("")
    lines.append("$remotes = git remote 2>$null")
    lines.append('if ($remotes -notcontains "origin") {')
    lines.append("    git remote add origin https://github.com/Kvasha62/Amazone_Clone.git")
    lines.append('    Write-Host "  remote add origin" -ForegroundColor Green')
    lines.append("} else {")
    lines.append('    Write-Host "  remote origin exists" -ForegroundColor Green')
    lines.append("}")
    lines.append("")
    lines.append("git add -A")
    lines.append("git commit -m \"Initial commit: Amazone Clone (Django 6.1 + React 19)\"")
    lines.append("")
    lines.append("Pop-Location")
    lines.append("")
    lines.append("# " + "=" * 69)
    lines.append("# Instructions")
    lines.append("# " + "=" * 69)
    lines.append("")
    lines.append('Write-Host ""')
    lines.append('Write-Host "  DEPLOY COMPLETE!" -ForegroundColor Green')
    lines.append('Write-Host ""')
    lines.append('Write-Host "Next steps:" -ForegroundColor Yellow')
    lines.append('Write-Host "  1. cd I:\\NewPythonProjects\\Amazone_Clone"')
    lines.append('Write-Host "  2. git push -u origin main"')
    lines.append('Write-Host "  3. If auth needed: use Personal Access Token as password"')
    lines.append('Write-Host ""')

    script_content = "\n".join(lines) + "\n"
    OUTPUT_SCRIPT.write_text(script_content, encoding="utf-8")

    total_lines = len(lines)
    total_bytes = len(script_content.encode("utf-8"))
    print(f"\nScript written: {OUTPUT_SCRIPT}")
    print(f"  Lines: {total_lines:,}")
    print(f"  Size: {total_bytes:,} bytes ({total_bytes/1024:.1f} KB)")
    print(f"  Backend: {be_count}, Frontend: {fe_count}")


if __name__ == "__main__":
    main()
