param(
  [string]$OutputDirectory = "D:\CodexWorkFiles\output"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseName = "personal-blog-release-20260815-v17"
$stagingRoot = Join-Path $OutputDirectory $releaseName
$zipPath = Join-Path $OutputDirectory "$releaseName.zip"

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
if (Test-Path -LiteralPath $stagingRoot) {
  Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null
$items = @(
  ".nojekyll",
  "404.html",
  "README.md",
  "index.html",
  "robots.txt",
  "rss.xml",
  "sitemap.xml",
  "blog-assets",
  "deploy",
  "performance",
  "resume-service"
)
foreach ($item in $items) {
  Copy-Item -LiteralPath (Join-Path $projectRoot $item) -Destination $stagingRoot -Recurse -Force
}

Get-ChildItem -LiteralPath $stagingRoot -Recurse -Directory -Filter "__pycache__" |
  Sort-Object FullName -Descending |
  Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $stagingRoot -Recurse -File -Include "*.pyc", "*.pyo" |
  Remove-Item -Force

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
Get-ChildItem -LiteralPath $stagingRoot -Recurse -File |
  Where-Object { $_.Extension -in @('.sh', '.service', '.py') } |
  ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    [System.IO.File]::WriteAllText($_.FullName, $content.Replace("`r`n", "`n"), $utf8NoBom)
  }

Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath
Write-Output "PACKAGE=$zipPath"
Write-Output "SHA256=$($hash.Hash)"
