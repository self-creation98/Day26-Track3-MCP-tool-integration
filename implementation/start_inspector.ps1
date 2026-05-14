$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverPath = (Join-Path $scriptDir "mcp_server.py").Replace("\", "/")
$pythonPath = ((Get-Command python).Source).Replace("\", "/")
$cachePath = Join-Path (Split-Path -Parent $scriptDir) ".npm-cache"

New-Item -ItemType Directory -Force -Path $cachePath | Out-Null
$env:NPM_CONFIG_CACHE = $cachePath

npx -y @modelcontextprotocol/inspector $pythonPath $serverPath
