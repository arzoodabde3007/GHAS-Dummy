---
description: Workflow 1 - Jira Manager - creates or closes Jira tickets. Dual-mode. Optimized.
model: claude-sonnet-4.5
tools:
  - powershell
---

# Workflow 1 — Jira Manager

**Purpose:** Upsert Jira tickets (create/close mode)  
**Modes:** create | close

## Steps

## CREATION MODE (Step 2 — Ticket Upsert)

### 1. Iterate over services with alerts

For each service in `$SERVICES`:

```powershell
foreach ($SERVICE_NAME in $SERVICES) {
    Write-Host "🔄 Processing service: $SERVICE_NAME"
```

### 2. Delta Detection — Compare Existing Ticket CVEs Against Current Alerts

**2a. Search for an existing active ticket:**

```powershell
    $searchLabelsList = if ($SEARCH_LABELS -and $SEARCH_LABELS -ne "<SEARCH_LABELS>") {
        $SEARCH_LABELS -split ','
    } else {
        @($BASE_LABEL)
    }
    $statusList   = ($SKIP_STATUSES | ForEach-Object { "`"$_`"" }) -join ", "
    $labelClauses = ($searchLabelsList | ForEach-Object { "labels = `"$($_.Trim())`"" }) -join " AND "
    $jql = "project = `"$JIRA_PROJECT`" AND $labelClauses AND labels = `"$SERVICE_NAME`" AND status in ($statusList)"
    if ($PARENT_JIRA -and $PARENT_JIRA -ne "null" -and $PARENT_JIRA -ne "<PARENT_JIRA>") {
        $jql += " AND parent = `"$PARENT_JIRA`""
    }
    $jql += " ORDER BY created DESC"

    $searchRaw = Invoke-WithRetry -Command { & $PYTHON_CMD $JIRA_SCRIPT search --jql $jql }
    $tickets = $searchRaw | ConvertFrom-Json
    Write-Host "  Search returned $($tickets.Count) ticket(s)"
```

**2b. Determine active ticket:**

```powershell
    $activeTicket = $tickets | Where-Object {
        $s = $_.status.ToLower()
        $SKIP_STATUSES | Where-Object { $_.ToLower() -eq $s }
    } | Select-Object -First 1

    if ($activeTicket) {
        $ACTIVE_TICKET_KEY    = $activeTicket.key
        $ACTIVE_TICKET_STATUS = $activeTicket.status
        Write-Host "  Found active ticket: $ACTIVE_TICKET_KEY (status: $ACTIVE_TICKET_STATUS)"
    } else {
        $ACTIVE_TICKET_KEY = "NONE"
        Write-Host "  No active ticket found"
    }
```

**2c. Fetch description for active ticket:**

```powershell
    if ($ACTIVE_TICKET_KEY -ne "NONE") {
        $getRaw = Invoke-WithRetry -Command { & $PYTHON_CMD $JIRA_SCRIPT get --ticket $ACTIVE_TICKET_KEY }
        $ticketDetail = $getRaw | ConvertFrom-Json
        $ACTIVE_TICKET_DESC = $ticketDetail.description_text.Substring(0, [Math]::Min(2000, $ticketDetail.description_text.Length))
    }
```

**2d. Run CVE delta detection:**

```powershell
    $tmpDesc = [System.IO.Path]::GetTempFileName() + ".txt"
    if ($ACTIVE_TICKET_KEY -ne "NONE") {
        Set-Content -Path $tmpDesc -Value $ACTIVE_TICKET_DESC -Encoding UTF8
    } else {
        Set-Content -Path $tmpDesc -Value "" -Encoding UTF8
    }

    $tmpPy = [System.IO.Path]::GetTempFileName() + ".py"
    @"
import csv, glob, os, re, json, tempfile

SERVICE = '$SERVICE_NAME'
CSV_PATH = r'$CSV_PATH'

with open(r'$tmpDesc', encoding='utf-8') as f:
    TICKET_DESC = f.read()

existing_ids = set(re.findall(r'CVE-\d{4}-\d+', TICKET_DESC, re.IGNORECASE))
existing_ids |= set(re.findall(r'GHSA-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+', TICKET_DESC, re.IGNORECASE))
existing_ids = {i.upper() for i in existing_ids}
print(f'EXISTING_IDS ({len(existing_ids)}): {sorted(existing_ids)[:5]}...' if len(existing_ids) > 5 else f'EXISTING_IDS ({len(existing_ids)}): {sorted(existing_ids)}')

with open(CSV_PATH, newline='', encoding='utf-8') as f:
    all_rows = list(csv.DictReader(f))

service_rows = [r for r in all_rows if r.get('service','').strip().lower() == SERVICE.lower()]
current_ids  = set()
for r in service_rows:
    if r.get('cve_id','').strip():  current_ids.add(r['cve_id'].strip().upper())
    if r.get('ghsa_id','').strip(): current_ids.add(r['ghsa_id'].strip().upper())
print(f'CURRENT_IDS ({len(current_ids)}): {sorted(current_ids)[:5]}...' if len(current_ids) > 5 else f'CURRENT_IDS ({len(current_ids)}): {sorted(current_ids)}')

new_ids = current_ids - existing_ids
print(f'NEW_IDS ({len(new_ids)}): {sorted(new_ids)[:5]}...' if len(new_ids) > 5 else f'NEW_IDS ({len(new_ids)}): {sorted(new_ids)}')

if not new_ids:
    print('DELTA_RESULT=NO_NEW_CVES')
else:
    new_rows = [r for r in service_rows
                if r.get('cve_id','').strip().upper()  in new_ids
                or r.get('ghsa_id','').strip().upper() in new_ids]
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False,
                                      newline='', encoding='utf-8')
    fieldnames = list(all_rows[0].keys())
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(new_rows)
    tmp.close()
    print(f'DELTA_RESULT=NEW_CVES_FOUND')
    print(f'DELTA_CSV={tmp.name}')
    print(f'DELTA_ROW_COUNT={len(new_rows)}')
"@ | Set-Content -Path $tmpPy -Encoding UTF8
    $deltaOutput = & $PYTHON_CMD $tmpPy
    Remove-Item $tmpPy, $tmpDesc -ErrorAction SilentlyContinue
    Write-Host "  Delta detection: $($deltaOutput[0])"
```

**Delta result actions:**

Parse output:
- `DELTA_RESULT=NO_NEW_CVES` → Set `JIRA_KEY = $ACTIVE_TICKET_KEY`, `JIRA_STATUS = SKIPPED` → jump to Step 4
- `DELTA_RESULT=NEW_CVES_FOUND` → Extract `DELTA_CSV` path → update existing ticket (Step 2e)

**2e. Update existing ticket description (only when `NEW_CVES_FOUND`):**

```powershell
    if ($DELTA_RESULT -eq "NEW_CVES_FOUND") {
        $updateOutput = Invoke-WithRetry -Command {
            & $PYTHON_CMD $JIRA_SCRIPT update-description --ticket "$ACTIVE_TICKET_KEY" --service "$SERVICE_NAME" --csv "$CSV_PATH"
        }
        Write-Host "  Updated ticket $ACTIVE_TICKET_KEY description"
        $JIRA_KEY = $ACTIVE_TICKET_KEY
        $JIRA_STATUS = "UPDATED"
    } else {
        $JIRA_KEY = $ACTIVE_TICKET_KEY
        $JIRA_STATUS = "SKIPPED"
    }
}
```

---

### 3. Create Jira Ticket (only when `$ACTIVE_TICKET_KEY = NONE`)

```powershell
if ($ACTIVE_TICKET_KEY -eq "NONE") {
    Write-Host "  Creating fresh ticket..."
    $createOutput = Invoke-WithRetry -Command {
        & $PYTHON_CMD $JIRA_SCRIPT create --project $JIRA_PROJECT --service "$SERVICE_NAME" --csv "$CSV_PATH"
    }
    $ticketJson = $createOutput | ConvertFrom-Json
    $JIRA_KEY = $ticketJson.key
    $JIRA_STATUS = "CREATED"
    Write-Host "  Created ticket: $JIRA_KEY"
}
```

---

### 4. Update the CSV with Jira Key and Status

```powershell
    $tmpPy = [System.IO.Path]::GetTempFileName() + ".py"
    @"
import csv

SERVICE     = '$SERVICE_NAME'
JIRA_KEY    = '$JIRA_KEY'
JIRA_STATUS = '$JIRA_STATUS'
CSV_PATH    = r'$CSV_PATH'

with open(CSV_PATH, newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if row.get('service', '').strip().lower() == SERVICE.strip().lower():
        row['jira_key']    = JIRA_KEY
        row['jira_status'] = JIRA_STATUS

fieldnames = list(rows[0].keys()) if rows else []
for col in ('jira_key', 'jira_status'):
    if col not in fieldnames:
        fieldnames.append(col)

with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'CSV updated for {SERVICE} -> {JIRA_KEY} ({JIRA_STATUS})')
"@ | Set-Content -Path $tmpPy -Encoding UTF8
    & $PYTHON_CMD $tmpPy
    Remove-Item $tmpPy -ErrorAction SilentlyContinue

}
```

---

## CLOSURE MODE (Step 2b — Zero-Alert Ticket Closure)

### 1. Iterate over zero-alert services

For each service in `$SERVICES`:

```powershell
foreach ($SERVICE_NAME in $SERVICES) {
    Write-Host "🔄 Processing zero-alert service: $SERVICE_NAME"

    $statusList   = ($SKIP_STATUSES | ForEach-Object { "`"$_`"" }) -join ", "
    $jql = "project = `"$JIRA_PROJECT`" AND labels = `"$BASE_LABEL`" AND labels = `"$SERVICE_NAME`" AND status in ($statusList)"
    if ($PARENT_JIRA -and $PARENT_JIRA -ne "null" -and $PARENT_JIRA -ne "<PARENT_JIRA>") {
        $jql += " AND parent = `"$PARENT_JIRA`""
    }
    $jql += " ORDER BY created DESC"

    $searchRaw = Invoke-WithRetry -Command { & $PYTHON_CMD $JIRA_SCRIPT search --jql $jql }
    $openTickets = $searchRaw | ConvertFrom-Json
    Write-Host "  Found $($openTickets.Count) open ticket(s)"

    foreach ($ticket in $openTickets) {
        $ticketKey = $ticket.key
        Write-Host "  Transitioning $ticketKey to Done..."
        Invoke-WithRetry -Command { & $PYTHON_CMD $JIRA_SCRIPT transition --ticket "$ticketKey" --name "Done" } | Out-Null
        Write-Host "  ✅ Transitioned $ticketKey"
    }

    if ($openTickets.Count -eq 0) {
        Write-Host "  No open tickets to close for $SERVICE_NAME"
    }
}
```

---

## Output to Orchestrator

### Creation mode:
```
W1 COMPLETE — TICKET CREATION
─────────────────────────────────────────
Jira results:
  CREATED (fresh)      : X  → [HMS-XX, ...]
  UPDATED (description): X  → [HMS-XX, ...]
  SKIPPED              : X  → [HMS-XX, ...]
  FAILED               : X  → (errors if any)
```

### Closure mode:
```
W1 COMPLETE — ZERO-ALERT CLOSURE
─────────────────────────────────────────
Tickets closed: X → [HMS-XX, ...]
```

## Rules
- One consolidated ticket per service — never one ticket per CVE
- Always search + delta before create — never skip it
- Active ticket (status in `$SKIP_STATUSES`) + new CVEs → update description in place; never create a separate delta ticket
- No active ticket → create fresh ticket covering all current alerts
- Search fails → log real error, continue with remaining services
- Ticket creation fails → log exact error, continue with remaining services
- Always run CSV update after every service in creation mode
- Use only config-loaded values for project, labels, priority, story points, and skip-status logic
