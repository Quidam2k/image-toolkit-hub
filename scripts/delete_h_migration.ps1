<#
    delete_h_migration.ps1  (one-off, July 2026)

    Deletes ONLY the Q: folders that passed SHA-256 verification
    (logs\h_migration_passed_20260722.txt). Refuses any path that would
    escape the project root. Reports reclaimed space.

    Run:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\delete_h_migration.ps1
#>
$q = 'Q:\Development\image_grid_sorter'
$passedFile = "$q\logs\h_migration_passed_20260722.txt"
$delLog = "$q\logs\h_migration_delete_20260722.log"

if (-not (Test-Path $passedFile)) { Write-Host "No passed-list found ($passedFile). Aborting."; exit 1 }
$passed = Get-Content $passedFile
$before = (Get-PSDrive Q).Free

function DLog($m) { $t = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m; Add-Content $delLog $t; Write-Host $t }
DLog "===== DELETE START ($($passed.Count) verified folders); Q free before bytes = $before ====="

foreach ($F in $passed) {
    $p = Join-Path $q $F
    $full = [System.IO.Path]::GetFullPath($p)
    if (-not $full.StartsWith("$q\", [StringComparison]::OrdinalIgnoreCase)) { DLog "$F : REFUSE (escapes project root: $full)"; continue }
    if (-not (Test-Path -LiteralPath $p)) { DLog "$F : already gone"; continue }
    try {
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop
        if (Test-Path -LiteralPath $p) { DLog "$F : ERROR still present" } else { DLog "$F : DELETED" }
    } catch { DLog "$F : ERROR $($_.Exception.Message)" }
}

$after = (Get-PSDrive Q).Free
$gb = [math]::Round(($after - $before) / 1GB, 1)
DLog "===== DELETE DONE; Q free after bytes = $after; reclaimed = $gb GB ====="
