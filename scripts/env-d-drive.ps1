# =============================================================================
# LoveWorld Care — Strict D:\ Drive Toolchain & Cache Isolation Bootstrap
# Ensures zero package caches, virtualenvs, Python runtimes, or temp artifacts
# are ever written to C:\ drive.
# =============================================================================

$ErrorActionPreference = "Stop"

$ToolchainRoot = "D:\.toolchains"
$WorkspaceRoot = "D:\Projects\LoveWorld Care"

$Directories = @(
    "$ToolchainRoot\pnpm-home",
    "$ToolchainRoot\pnpm-store",
    "$ToolchainRoot\npm-cache",
    "$ToolchainRoot\uv-cache",
    "$ToolchainRoot\uv-python",
    "$ToolchainRoot\pip-cache",
    "$ToolchainRoot\playwright-browsers",
    "$ToolchainRoot\tmp",
    "$WorkspaceRoot\.turbo"
)

foreach ($Dir in $Directories) {
    if (-not (Test-Path -Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    }
}

# Node / pnpm / npm / Turbo
$env:PNPM_HOME = "$ToolchainRoot\pnpm-home"
$env:NPM_CONFIG_STORE_DIR = "$ToolchainRoot\pnpm-store"
$env:NPM_CONFIG_CACHE = "$ToolchainRoot\npm-cache"
$env:TURBO_CACHE_DIR = "$WorkspaceRoot\.turbo"

# Python / uv / pip / pytest
$env:UV_CACHE_DIR = "$ToolchainRoot\uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$ToolchainRoot\uv-python"
$env:UV_PROJECT_ENVIRONMENT = "$WorkspaceRoot\.venv"
$env:PIP_CACHE_DIR = "$ToolchainRoot\pip-cache"
$env:PYTHONPYCACHEPREFIX = "$ToolchainRoot\tmp\pycache"

# System temporary directories for builds
$env:TEMP = "$ToolchainRoot\tmp"
$env:TMP = "$ToolchainRoot\tmp"
$env:PLAYWRIGHT_BROWSERS_PATH = "$ToolchainRoot\playwright-browsers"

if ($env:PATH -notlike "*$env:PNPM_HOME*") {
    $env:PATH = "$env:PNPM_HOME;$env:PATH"
}

Write-Host "[LoveWorld Care] D:\ Drive Toolchain Isolation Active" -ForegroundColor Cyan
Write-Host "  PNPM Store : $env:NPM_CONFIG_STORE_DIR" -ForegroundColor Gray
Write-Host "  UV Cache   : $env:UV_CACHE_DIR" -ForegroundColor Gray
Write-Host "  UV Venv    : $env:UV_PROJECT_ENVIRONMENT" -ForegroundColor Gray
Write-Host "  Temp Dir   : $env:TEMP" -ForegroundColor Gray
