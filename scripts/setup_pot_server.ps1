# Clones and builds the bgutil PO-token server into vendor/bgutil-server/,
# so the app can use it locally in dev mode for best-quality downloads.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VendorDir = Join-Path $ProjectRoot "vendor\bgutil-server"
$CloneDir = Join-Path $ProjectRoot "vendor\.bgutil-src"
$BgutilVersion = "1.3.1"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "A Node.js (>=20) szukseges ehhez a scripthez, de nem talalhato a PATH-on."
    exit 1
}

Remove-Item -Recurse -Force $VendorDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $CloneDir -ErrorAction SilentlyContinue

git clone --depth 1 --single-branch --branch $BgutilVersion `
  https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git $CloneDir

Push-Location (Join-Path $CloneDir "server")
npm ci
npx tsc
Pop-Location

New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null
Move-Item (Join-Path $CloneDir "server\build") (Join-Path $VendorDir "build")
Move-Item (Join-Path $CloneDir "server\node_modules") (Join-Path $VendorDir "node_modules")
Remove-Item -Recurse -Force $CloneDir

Write-Host "Kesz. A PO-token szerver build kimenete: $VendorDir\build\main.js"
