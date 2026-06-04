<#
.SYNOPSIS
    Deploy personal skills to global skill directories of AI coding assistants.

.DESCRIPTION
    Creates junctions (Windows symlinks) to deploy skills to Claude Code and Codex.
    Copies files and registers in workspace skill.json for QwenPaw (all workspaces).

.PARAMETER List
    List all deployable skills (self-developed and global).

.PARAMETER Skill
    Specify the skill slug to deploy.

.PARAMETER Target
    Target platform: claude-code, codex, qwenpaw, all.

.PARAMETER Source
    Skill source for QwenPaw: self (my-skills/skills/) or global (~/.agents/skills/).
    Ignored for claude-code and codex targets.

.PARAMETER Description
    Chinese description for QwenPaw skill discovery. If omitted, falls back to
    SKILL.md frontmatter description or existing workspace skill.json entry.

.PARAMETER All
    Deploy all self-developed skills to all platforms.

.PARAMETER Uninstall
    Remove deployment for a skill.

.EXAMPLE
    .\deploy.ps1 -List
    .\deploy.ps1 -Skill follow-ai-coding-builders -Target claude-code
    .\deploy.ps1 -Skill brainstorming -Target qwenpaw -Source global
    .\deploy.ps1 -Skill weekly-report -Target qwenpaw -Description "..."
    .\deploy.ps1 -All
#>

param(
    [switch]$List,
    [string]$Skill,
    [ValidateSet("claude-code", "codex", "qwenpaw", "all")]
    [string]$Target = "claude-code",
    [ValidateSet("self", "global")]
    [string]$Source = "self",
    [string]$Description = "",
    [switch]$All,
    [switch]$Uninstall
)

# ============================================================
# Configuration
# ============================================================

$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptRoot "skills"

$Targets = @{
    "claude-code" = @(
        (Join-Path $env:USERPROFILE ".agents\skills"),
        (Join-Path $env:USERPROFILE ".claude\skills")
    )
    "codex" = @(
        (Join-Path $env:USERPROFILE ".codex\skills")
    )
    "qwenpaw" = @()
}

$QwenPawWorkspacesRoot = Join-Path $env:USERPROFILE ".qwenpaw\workspaces"

# ============================================================
# Helper Functions
# ============================================================

function Get-AvailableSkills {
    if (-not (Test-Path $SkillsDir)) {
        Write-Host "Error: skills directory not found ($SkillsDir)" -ForegroundColor Red
        return @()
    }
    Get-ChildItem -Path $SkillsDir -Directory | ForEach-Object { $_.Name }
}

function Get-GlobalSkills {
    $globalDir = Join-Path $env:USERPROFILE ".agents\skills"
    if (-not (Test-Path $globalDir)) { return @() }
    Get-ChildItem -Path $globalDir -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "SKILL.md")
    } | ForEach-Object { $_.Name }
}

function Get-SkillSourceDir {
    param(
        [string]$SkillName,
        [string]$Src
    )
    if ($Src -eq "global") {
        return Join-Path $env:USERPROFILE ".agents\skills\$SkillName"
    }
    return Join-Path $SkillsDir $SkillName
}

function Get-SkillMdDescription {
    param([string]$SkillDir)
    $skillFile = Join-Path $SkillDir "SKILL.md"
    if (-not (Test-Path $skillFile)) { return "" }
    $content = Get-Content $skillFile -Raw -Encoding UTF8
    if ($content -match '(?s)^---\s*\r?\n(.*?)\r?\n---') {
        $frontmatter = $Matches[1]
        if ($frontmatter -match '(?m)^description:\s*["'']?(.+?)["'']?\s*$') {
            return $Matches[1].Trim()
        }
    }
    return ""
}

function Get-QwenPawWorkspaces {
    if (-not (Test-Path $QwenPawWorkspacesRoot)) { return @() }
    Get-ChildItem -Path $QwenPawWorkspacesRoot -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "skill.json")
    } | ForEach-Object { $_.Name }
}

# ============================================================
# QwenPaw Workspace Manifest Functions
# ============================================================

function Read-WorkspaceManifest {
    param([string]$WorkspaceId)
    $manifestPath = Join-Path $QwenPawWorkspacesRoot "$WorkspaceId\skill.json"
    if (-not (Test-Path $manifestPath)) { return $null }
    return (Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Write-WorkspaceManifest {
    param(
        [string]$WorkspaceId,
        [object]$Manifest
    )
    $manifestPath = Join-Path $QwenPawWorkspacesRoot "$WorkspaceId\skill.json"
    $json = $Manifest | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($manifestPath, $json, $Utf8NoBom)
}

function Get-QwenPawDeployedSkills {
    $result = @{}
    $workspaces = Get-QwenPawWorkspaces
    foreach ($ws in $workspaces) {
        $manifest = Read-WorkspaceManifest -WorkspaceId $ws
        if ($null -eq $manifest) { continue }
        foreach ($prop in $manifest.skills.PSObject.Properties) {
            if ($prop.Value.source -eq "customized") {
                if (-not $result.ContainsKey($prop.Name)) { $result[$prop.Name] = @() }
                if ($ws -notin $result[$prop.Name]) { $result[$prop.Name] += $ws }
            }
        }
    }
    return $result
}

# ============================================================
# Deployment Status
# ============================================================

function Get-DeployedSkills {
    $deployed = @{}
    foreach ($platform in $Targets.Keys) {
        if ($platform -eq "qwenpaw") { continue }
        foreach ($targetDir in $Targets[$platform]) {
            if (Test-Path $targetDir) {
                $links = Get-ChildItem -Path $targetDir -Directory | Where-Object {
                    $_.Attributes -match "ReparsePoint"
                }
                foreach ($link in $links) {
                    if (-not $deployed.ContainsKey($link.Name)) { $deployed[$link.Name] = @() }
                    if ($platform -notin $deployed[$link.Name]) { $deployed[$link.Name] += $platform }
                }
            }
        }
    }
    # QwenPaw: check workspace manifests
    $qpSkills = Get-QwenPawDeployedSkills
    foreach ($name in $qpSkills.Keys) {
        if (-not $deployed.ContainsKey($name)) { $deployed[$name] = @() }
        if ("qwenpaw" -notin $deployed[$name]) { $deployed[$name] += "qwenpaw" }
    }
    return $deployed
}

# ============================================================
# List Display
# ============================================================

function Show-List {
    $skills = Get-AvailableSkills
    $globalSkills = Get-GlobalSkills
    $deployed = Get-DeployedSkills

    Write-Host ""
    Write-Host "=== Self-developed Skills ===" -ForegroundColor Cyan
    if ($skills.Count -eq 0) {
        Write-Host "  (none)" -ForegroundColor DarkGray
    }
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
    Write-Host "=== Global Open-source Skills (QwenPaw-ready) ===" -ForegroundColor Cyan
    if ($globalSkills.Count -eq 0) {
        Write-Host "  (none)" -ForegroundColor DarkGray
    }
    foreach ($s in $globalSkills) {
        $qpDeployed = $deployed.ContainsKey($s) -and "qwenpaw" -in $deployed[$s]
        $status = if ($qpDeployed) { "Deployed to QwenPaw" } else { "Not deployed to QwenPaw" }
        $color = if ($qpDeployed) { "Green" } else { "DarkGray" }
        Write-Host "  $s" -NoNewline
        Write-Host "  [$status]" -ForegroundColor $color
    }
    Write-Host ""
}

# ============================================================
# Deploy Functions
# ============================================================

function Deploy-Skill {
    param(
        [string]$SkillName,
        [string]$Platform
    )

    if ($Platform -eq "qwenpaw") {
        return Deploy-QwenPawSkill -SkillName $SkillName
    }

    $sourceDir = Join-Path $SkillsDir $SkillName
    $targetDirs = $Targets[$Platform]

    if (-not (Test-Path $sourceDir)) {
        Write-Host "Error: Skill '$SkillName' not found" -ForegroundColor Red
        return $false
    }

    $allSuccess = $true
    foreach ($targetDir in $targetDirs) {
        if (-not (Test-Path $targetDir)) {
            Write-Host "Target directory not found, creating: $targetDir" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        $linkPath = Join-Path $targetDir $SkillName

        if (Test-Path $linkPath) {
            $item = Get-Item $linkPath
            if ($item.Attributes -match "ReparsePoint") {
                Write-Host "  [SKIP] $SkillName already deployed to $targetDir" -ForegroundColor Green
                continue
            } else {
                Write-Host "  [WARN] $linkPath exists but is not a symlink" -ForegroundColor Red
                $allSuccess = $false
                continue
            }
        }

        Write-Host "  [DEPLOY] $SkillName -> $targetDir" -ForegroundColor Cyan
        cmd /c mklink /J "`"$linkPath`"" "`"$sourceDir`"" | Out-Null

        if (Test-Path $linkPath) {
            Write-Host "  [OK] $SkillName deployed to $targetDir" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Failed to deploy $SkillName to $targetDir" -ForegroundColor Red
            $allSuccess = $false
        }
    }
    return $allSuccess
}

function Deploy-QwenPawSkill {
    param([string]$SkillName)

    $sourceDir = Get-SkillSourceDir -SkillName $SkillName -Src $Source

    if (-not (Test-Path $sourceDir)) {
        Write-Host "Error: Skill '$SkillName' not found at $sourceDir" -ForegroundColor Red
        return $false
    }

    $skillFile = Join-Path $sourceDir "SKILL.md"
    if (-not (Test-Path $skillFile)) {
        Write-Host "Error: SKILL.md not found in $sourceDir" -ForegroundColor Red
        return $false
    }

    $workspaces = Get-QwenPawWorkspaces
    if ($workspaces.Count -eq 0) {
        Write-Host "Error: No QwenPaw workspaces found" -ForegroundColor Red
        return $false
    }

    # Determine description (same for all workspaces)
    $desc = $Description
    if ([string]::IsNullOrWhiteSpace($desc)) {
        $desc = Get-SkillMdDescription -SkillDir $sourceDir
    }

    $allSuccess = $true
    foreach ($ws in $workspaces) {
        Write-Host "  Workspace: $ws" -ForegroundColor White
        $manifest = Read-WorkspaceManifest -WorkspaceId $ws
        if ($null -eq $manifest) {
            Write-Host "    [SKIP] Cannot read manifest" -ForegroundColor Yellow
            continue
        }

        # Refuse to overwrite builtin skills
        if ((Get-Member -InputObject $manifest.skills -Name $SkillName) -and
            $manifest.skills.$SkillName.source -eq "builtin") {
            Write-Host "    [SKIP] '$SkillName' is a builtin skill in this workspace" -ForegroundColor Yellow
            continue
        }

        # Keep existing description if updating
        $useDesc = $desc
        if ([string]::IsNullOrWhiteSpace($useDesc) -and
            (Get-Member -InputObject $manifest.skills -Name $SkillName)) {
            $useDesc = $manifest.skills.$SkillName.metadata.description
        }

        # Copy files to workspace
        $wsSkillsDir = Join-Path $QwenPawWorkspacesRoot "$ws\skills\$SkillName"
        if (-not (Test-Path $wsSkillsDir)) {
            New-Item -ItemType Directory -Path $wsSkillsDir -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $sourceDir "*") -Destination $wsSkillsDir -Recurse -Force
        Write-Host "    [COPY] files -> workspace" -ForegroundColor Cyan

        # Register in workspace skill.json
        $timestamp = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffffZ")
        $existingEntry = (Get-Member -InputObject $manifest.skills -Name $SkillName)

        if ($existingEntry) {
            $manifest.skills.$SkillName.metadata.description = $useDesc
            $manifest.skills.$SkillName.updated_at = $timestamp
            $manifest.skills.$SkillName.metadata.updated_at = $timestamp
            Write-Host "    [UPDATE] skill.json entry" -ForegroundColor Cyan
        } else {
            $skillEntry = [PSCustomObject]@{
                enabled      = $true
                channels     = @("all")
                source       = "customized"
                metadata     = [PSCustomObject]@{
                    name          = $SkillName
                    description   = $useDesc
                    version_text  = "1.0"
                    commit_text   = ""
                    source        = "customized"
                    protected     = $false
                    requirements  = [PSCustomObject]@{
                        require_bins = @()
                        require_envs = @()
                    }
                    updated_at    = $timestamp
                }
                requirements = [PSCustomObject]@{
                    require_bins = @()
                    require_envs = @()
                }
                updated_at   = $timestamp
                config       = [PSCustomObject]@{}
            }
            $manifest.skills | Add-Member -NotePropertyName $SkillName -NotePropertyValue $skillEntry -Force
            Write-Host "    [ADD] skill.json entry" -ForegroundColor Cyan
        }

        $manifest.version = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
        Write-WorkspaceManifest -WorkspaceId $ws -Manifest $manifest
        Write-Host "    [OK] $SkillName deployed to workspace $ws" -ForegroundColor Green
    }
    return $allSuccess
}

# ============================================================
# Uninstall Functions
# ============================================================

function Uninstall-Skill {
    param(
        [string]$SkillName,
        [string]$Platform
    )

    if ($Platform -eq "qwenpaw") {
        Uninstall-QwenPawSkill -SkillName $SkillName
        return
    }

    $targetDirs = $Targets[$Platform]
    foreach ($targetDir in $targetDirs) {
        $linkPath = Join-Path $targetDir $SkillName

        if (-not (Test-Path $linkPath)) {
            Write-Host "  [SKIP] $SkillName not deployed to $targetDir" -ForegroundColor Yellow
            continue
        }

        Write-Host "  [REMOVE] $SkillName from $targetDir" -ForegroundColor Cyan
        cmd /c rmdir "`"$linkPath`"" | Out-Null
        Write-Host "  [DONE] Removed $SkillName from $targetDir" -ForegroundColor Green
    }
}

function Uninstall-QwenPawSkill {
    param([string]$SkillName)

    $workspaces = Get-QwenPawWorkspaces
    foreach ($ws in $workspaces) {
        Write-Host "  Workspace: $ws" -ForegroundColor White

        # Remove skill directory
        $wsSkillsDir = Join-Path $QwenPawWorkspacesRoot "$ws\skills\$SkillName"
        if (Test-Path $wsSkillsDir) {
            Remove-Item -Path $wsSkillsDir -Recurse -Force
            Write-Host "    [DONE] Removed skill directory" -ForegroundColor Green
        } else {
            Write-Host "    [SKIP] Skill directory not found" -ForegroundColor Yellow
        }

        # Remove from workspace skill.json
        $manifest = Read-WorkspaceManifest -WorkspaceId $ws
        if ($null -eq $manifest) { continue }

        if (-not (Get-Member -InputObject $manifest.skills -Name $SkillName)) {
            Write-Host "    [SKIP] Not in skill.json" -ForegroundColor Yellow
            continue
        }

        if ($manifest.skills.$SkillName.source -eq "builtin") {
            Write-Host "    [WARN] Builtin skill, skipping removal" -ForegroundColor Red
            continue
        }

        $manifest.skills.PSObject.Properties.Remove($SkillName)
        $manifest.version = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
        Write-WorkspaceManifest -WorkspaceId $ws -Manifest $manifest
        Write-Host "    [DONE] Removed from skill.json" -ForegroundColor Green
    }
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
    $platforms = if ($Target -eq "all") { $Targets.Keys } else { @($Target) }
    foreach ($platform in $platforms) {
        Deploy-Skill -SkillName $Skill -Platform $platform
    }
    exit
}

if ($All) {
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
Write-Host "  -Target <platform>            Target: claude-code, codex, qwenpaw, all"
Write-Host "  -Source <self|global>         Skill source for QwenPaw (default: self)"
Write-Host "  -Description <text>           Chinese description for QwenPaw discovery"
Write-Host "  -All                          Deploy all self-developed skills to all platforms"
Write-Host "  -Uninstall                    Remove deployment (use with -Skill)"
Write-Host ""
Write-Host "Examples:" -ForegroundColor Cyan
Write-Host "  .\deploy.ps1 -List"
Write-Host "  .\deploy.ps1 -Skill follow-ai-coding-builders -Target claude-code"
Write-Host "  .\deploy.ps1 -Skill weekly-report -Target qwenpaw"
Write-Host "  .\deploy.ps1 -Skill brainstorming -Target qwenpaw -Source global"
Write-Host "  .\deploy.ps1 -Skill brainstorming -Target qwenpaw -Uninstall"
Write-Host "  .\deploy.ps1 -All"
Write-Host ""
