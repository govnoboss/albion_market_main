$ErrorActionPreference = "Stop"

# Try to find flyctl
$flyPath = "$env:USERPROFILE\.fly\bin\flyctl.exe"
if (-not (Test-Path $flyPath)) {
    Write-Host "Flyctl not found at default location. Checking PATH..." -ForegroundColor Yellow
    $flyPath = (Get-Command flyctl -ErrorAction SilentlyContinue).Source
    if (-not $flyPath) {
        $flyPath = (Get-Command fly -ErrorAction SilentlyContinue).Source
    }
}

if (-not $flyPath) {
    Write-Error "Could not find flyctl! Please install it first."
}

Write-Host "Using Flyctl at: $flyPath" -ForegroundColor Cyan

# 1. Login Check
Write-Host "`n[1/3] Checking Authentication..." -ForegroundColor Cyan
& $flyPath auth whoami
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Opening browser for login..." -ForegroundColor Yellow
    & $flyPath auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Login failed!"
    }
}

# 2. Set Secrets
Write-Host "`n[2/3] Setting Secrets (Private Key)..." -ForegroundColor Cyan
$keyPath = Join-Path $PSScriptRoot "..\keys\private.pem"
if (-not (Test-Path $keyPath)) {
    Write-Error "Private key not found at $keyPath"
}

$privateKey = Get-Content $keyPath -Raw
# We need to handle the secret setting carefully. 
# Using stdin is safer for multiline values.
$privateKey | & $flyPath secrets set LICENSE_PRIVATE_KEY=- --app gbot-license

if ($LASTEXITCODE -eq 0) {
    Write-Host "Secret set successfully!" -ForegroundColor Green
} else {
    Write-Error "Failed to set secret!"
}

# 3. Deploy
Write-Host "`n[3/3] Deploying Server..." -ForegroundColor Cyan
Set-Location (Join-Path $PSScriptRoot "..\server")
& $flyPath deploy

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
} else {
    Write-Error "Deployment failed!"
}
