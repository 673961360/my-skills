<#
.SYNOPSIS
    Deploy personal skills to global skill directories of AI coding assistants.

.DESCRIPTION
    Creates junctions (Windows symlinks) to deploy skills to target platforms.
    Supports Claude Code (~/.agents/skills) and Codex (~/.codex/skills).

    QwenPaw is intentionally excluded from auto-deploy because it uses a
    centralized skill.json index in skill_pool/. Manual verification required
    before adding support. See README.md for details.

.PARAMETER List
    List all deployable skills.

.PARAMETER Skill
    Specify the skill slug to deploy.

.PARAMETER Target
    Target platform: claude-code, codex, all.

.PARAMETER All
    Deploy all skills to all platforms.

.PARAMETER Uninstall
    Remove symlinks for a skill.

.EXAMPLE
    .\deploy.ps1 -List
    .\deploy.ps1 -Skill follow-ai-coding-builders -Target claude-code
    .\deploy.ps1 -All
#>

param(
    [switch]$List,
    [string]$Skill,
    [ValidateSet("claude-code", "codex", "all")]
    [string]$Target = "claude-code",
    [switch]$All,
    [switch]$Uninstall
)

# ============================================================
# Configuration
# ============================================================

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptRoot "skills"

# Global skill directories for each platform
$Targets = @{
    # Claude Code uses the cross-agent standard location (~/.agents/skills)
    "claude-code" = Join-Path $env:USERPROFILE ".agents\skills"
    "codex"       = Join-Path $env:USERPROFILE ".codex\skills"
    # QwenPaw excluded: uses centralized skill.json index, auto-discovery unverified
}

# ============================================================
# Functions
# ============================================================

function Get-AvailableSkills {
    if (-not (Test-Path $SkillsDir)) {
        Write-Host "Error: skills directory not found ($SkillsDir)" -ForegroundColor Red
        return @()
    }
    Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object { $_.Name }
}

function Get-DeployedSkills {
    $deployed = @{}
    foreach ($platform in $Targets.Keys) {
        $targetDir = $Targets[$platform]
        if (Test-Path $targetDir) {
            $links = Get-ChildItem -Path $targetDir -Directory | Where-Object {
                $_.Attributes -match "ReparsePoint"
            }
            foreach ($link in $links) {
                if (-not $deployed.ContainsKey($link.Name)) {
                    $deployed[$link.Name] = @()
                }
                $deployed[$link.Name] += $platform
            }
        }
    }
    return $deployed
}

function Show-List {
    $skills = Get-AvailableSkills
    $deployed = Get-DeployedSkills

    Write-Host ""
    Write-Host "=== Deployable Skills ===" -ForegroundColor Cyan
    foreach ($s in $skills) {
        $status = "Not deployed"
        $color = "Yellow"
        if ($deployed.ContainsKey($s)) {
            $status = "Deployed to: " + ($deployed[$s] -join ", ")
            $color = "Green"
        }
        Write-Host "  $s" -NoNewline
        Write-Host "  [$status]" -ForegroundColor $color
    }
    Write-Host ""
}

function Deploy-Skill {
    param(
        [string]$SkillName,
        [string]$Platform
    )

    $sourceDir = Join-Path $SkillsDir $SkillName
    $targetDir = $Targets[$Platform]

    if (-not (Test-Path $sourceDir)) {
        Write-Host "Error: Skill '$SkillName' not found" -ForegroundColor Red
        return $false
    }

    if (-not (Test-Path $targetDir)) {
        Write-Host "Target directory not found, creating: $targetDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    $linkPath = Join-Path $targetDir $SkillName

    if (Test-Path $linkPath) {
        $item = Get-Item $linkPath
        if ($item.Attributes -match "ReparsePoint") {
            Write-Host "  [SKIP] $SkillName already deployed to $Platform" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [WARN] $linkPath exists but is not a symlink" -ForegroundColor Red
            return $false
        }
    }

    # Create Junction (Windows directory symlink)
    Write-Host "  [DEPLOY] $SkillName -> $Platform" -ForegroundColor Cyan
    $result = cmd /c mklink /J "`"$linkPath`"" "`"$sourceDir`""

    if (Test-Path $linkPath) {
        Write-Host "  [OK] $SkillName deployed to $Platform" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [FAIL] Failed to deploy $SkillName to $Platform" -ForegroundColor Red
        return $false
    }
}

function Uninstall-Skill {
    param(
        [string]$SkillName,
        [string]$Platform
    )

    $targetDir = $Targets[$Platform]
    $linkPath = Join-Path $targetDir $SkillName

    if (-not (Test-Path $linkPath)) {
        Write-Host "  [SKIP] $SkillName not deployed to $Platform" -ForegroundColor Yellow
        return
    }

    Write-Host "  [REMOVE] $SkillName from $Platform" -ForegroundColor Cyan
    cmd /c rmdir "`"$linkPath`"" | Out-Null
    Write-Host "  [DONE] Removed $SkillName from $Platform" -ForegroundColor Green
}

# ============================================================
# Main Logic
# ============================================================

if ($List) {
    Show-List
    exit
}

if ($Uninstall -and $Skill) {
    $platforms = if ($Target -eq "all") { $Targets.Keys } else { @($Target) }
    foreach ($platform in $platforms) {
        Uninstall-Skill -SkillName $Skill -Platform $platform
    }
    exit
}

if ($Skill) {
    # Deploy single skill
    $platforms = if ($Target -eq "all") { $Targets.Keys } else { @($Target) }
    foreach ($platform in $platforms) {
        Deploy-Skill -SkillName $Skill -Platform $platform
    }
    exit
}

if ($All) {
    # Deploy all skills to all platforms
    $skills = Get-AvailableSkills
    $platforms = $Targets.Keys
    foreach ($s in $skills) {
        Write-Host ""
        Write-Host "--- Deploying: $s ---" -ForegroundColor White
        foreach ($platform in $platforms) {
            Deploy-Skill -SkillName $s -Platform $platform
        }
    }
    Write-Host ""
    exit
}

# Default: show help
Write-Host "Usage: .\deploy.ps1 [options]" -ForegroundColor Cyan
Write-Host ""
Write-Host "Options:" -ForegroundColor Cyan
Write-Host "  -List                         List all deployable skills"
Write-Host "  -Skill <slug>                 Deploy specified skill (default target: claude-code)"
Write-Host "  -Target <platform>            Target platform: claude-code, codex, all"
Write-Host "  -All                          Deploy all skills to all platforms"
Write-Host "  -Uninstall                    Remove symlinks (use with -Skill)"
Write-Host ""
Write-Host "Examples:" -ForegroundColor Cyan
Write-Host "  .\deploy.ps1 -List"
Write-Host "  .\deploy.ps1 -Skill follow-ai-coding-builders -Target claude-code"
Write-Host "  .\deploy.ps1 -All"
Write-Host ""
