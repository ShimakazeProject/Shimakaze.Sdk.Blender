# Builds the Shimakaze SDK extension with Blender's official build command.
#
# Usage:
#   .\build.ps1                      # use "blender" from PATH
#   .\build.ps1 -Blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
#
# The extension source lives in extension/ (manifest + package), which is
# passed straight to Blender:
#   blender --command extension build --source-dir extension --output-dir dist

param(
    [string]$Blender = "blender"
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$SourceDir = Join-Path $Root "extension"
$OutDir = Join-Path $Root "dist"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Write-Host "Building extension from $SourceDir ..."
& $Blender --command extension build --source-dir $SourceDir --output-dir $OutDir
if ($LASTEXITCODE -ne 0) {
    throw "Blender build failed with exit code $LASTEXITCODE"
}

Write-Host "Built:"
Get-ChildItem -Path $OutDir -Filter "*.zip" | ForEach-Object { Write-Host "  $($_.FullName)" }
