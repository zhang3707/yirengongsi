# 启动 Pilot 开发环境（API + Console）。
# 用法：powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "== AI Company MVP v1.0 · Pilot 开发环境 ==" -ForegroundColor Cyan
python scripts/seed.py
Write-Host "控制台: http://localhost:8000/console/  API 文档: http://localhost:8000/docs" -ForegroundColor Green
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
