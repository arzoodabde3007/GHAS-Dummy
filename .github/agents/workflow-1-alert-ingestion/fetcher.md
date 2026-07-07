---
description: Workflow 1 - Fetcher - runs fetch_alerts.sh to pull all GitHub alerts. Optimized.
model: claude-haiku-4.5
tools:
  - powershell
---

# Workflow 1 — Fetcher

**Purpose:** Fetch all GitHub alerts (Dependabot, Code Scanning, Secret Scanning)  
**Output:** Consolidated CSV file with all alerts

## Prerequisites
- GitHub CLI authenticated (`gh auth login`)
- `jq` available

## Steps

### 0. Load Config

```powershell
$CONFIG_PATH   = "<CONFIG_PATH>"
$SERVICES_JSON = "<SERVICES_JSON>"
$REPO_ROOT     = "<REPO_ROOT>"
$GIT_BASH      = "<GIT_BASH>"
$GH_CMD        = "<GH_CMD>"
$PYTHON_CMD    = "<PYTHON_CMD>"
$FETCH_SCRIPT  = "<FETCH_SCRIPT>"
$REPO_OWNER    = "<REPO_OWNER>"
$CSV_OUT_DIR   = Split-Path $FETCH_SCRIPT -Parent

Write-Host "Config loaded: repo_root=$REPO_ROOT  services=$($SERVICES_JSON | ConvertFrom-Json | ForEach-Object { $_.name } | Join-String -Separator ',')"
```

### 1. Verify GitHub CLI authentication

```bash
$GH_CMD auth status
```

Stop if not authenticated.

### 2. Parse services and prepare for consolidated fetch

```powershell
$services = $SERVICES_JSON | ConvertFrom-Json
$serviceCount = @($services).Count
Write-Host "Fetching alerts for $serviceCount service(s): $(($services | ForEach-Object { $_.name }) -join ', ')"
```

### 3. Run fetch_alerts.sh for each service

```powershell
$CSV_OUT_DIR_UNIX = $CSV_OUT_DIR -replace '\\', '/'
$FETCH_SCRIPT_UNIX = $FETCH_SCRIPT -replace '\\', '/'

foreach ($svc in $services) {
    & $GIT_BASH -c "$FETCH_SCRIPT_UNIX $CSV_OUT_DIR_UNIX $($svc.name) $REPO_OWNER $($svc.github_repo)"
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
```

### 4. Resolve the consolidated CSV file path

```powershell
$latestCsv = Get-ChildItem (Join-Path $CSV_OUT_DIR 'github_alerts_*.csv') | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latestCsv) { Write-Host "❌ FAILED: No CSV file found"; exit 1 }
$CSV_PATH = $latestCsv.FullName
Write-Host "✅ CSV path: $CSV_PATH"
```

### 5. Extract metrics

```powershell
$tmpPy = [System.IO.Path]::GetTempFileName() + ".py"
$svcJson = $SERVICES_JSON | ConvertTo-Json -Compress | % { $_ -replace '"', '\"' }
@"
import csv, json
CSV_PATH = r'$CSV_PATH'
all_svcs = {s['name'] for s in json.loads('$svcJson')}
with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))
    alerts_by_svc = set(r.get('service','').strip() for r in rows if r.get('service'))
    zero_svcs = ','.join(sorted(all_svcs - alerts_by_svc))
print(f'TOTAL_ALERTS={len(rows)}')
print(f'NONZERO_ALERT_SERVICES={",".join(sorted(alerts_by_svc))}')
print(f'ZERO_ALERT_SERVICES={zero_svcs}')
"@ | Set-Content -Path $tmpPy -Encoding UTF8
& $PYTHON_CMD $tmpPy
Remove-Item $tmpPy
```

### 6. Return Results

```powershell
Write-Host "CSV_PATH=$CSV_PATH"
Write-Host "TOTAL_ALERT_COUNT=$TOTAL_ALERT_COUNT"
Write-Host "NONZERO_ALERT_SERVICES=$NONZERO_ALERT_SERVICES"
Write-Host "ZERO_ALERT_SERVICES=$ZERO_ALERT_SERVICES"
```

## Output
- `TOTAL_ALERTS` — count
- `NONZERO_ALERT_SERVICES` — comma-separated  
- `ZERO_ALERT_SERVICES` — comma-separated
- `CSV_PATH` — file path
