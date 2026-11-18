Set-Location -Path $PSScriptRoot
$ErrorActionPreference = "Stop"

$PY = 'C:\Users\$M\PycharmProjects\PythonProject\.venv\Scripts\python.exe'

& $PY src\train_models.py
if ($LASTEXITCODE -ne 0) { throw "train_models.py failed" }

& $PY src\build_report.py
if ($LASTEXITCODE -ne 0) { throw "build_report.py failed" }

Write-Host "`nDone! Check results/ and the .docx file." -ForegroundColor Green
Read-Host "Press Enter to close"