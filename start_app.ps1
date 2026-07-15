$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'

$pythonExe = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe'
$nodeExe = 'C:\Program Files\nodejs\node.exe'
$npmCli = 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js'

Write-Host 'Starting Road Beyond the Pines Studio...' -ForegroundColor Cyan

$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectRoot -PassThru
$frontendProcess = Start-Process -FilePath $nodeExe -ArgumentList @($npmCli,'run','dev','--','--host','127.0.0.1','--port','5173') -WorkingDirectory $frontendRoot -PassThru

Write-Host 'Backend started at http://127.0.0.1:8000' -ForegroundColor Green
Write-Host 'Frontend started at http://127.0.0.1:5173' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop the processes.' -ForegroundColor Yellow

try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
}
finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force
    }
}
