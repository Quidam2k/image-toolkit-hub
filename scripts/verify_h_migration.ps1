<#
    verify_h_migration.ps1  (one-off, July 2026)

    Proves that every file in each Q: scope folder is present AND byte-identical
    (SHA-256) on H:\ImageRepository BEFORE anything is deleted. Honors the user's
    hard requirement: "make damn sure the copies are good before you delete anything."

    Per folder:
      1. Structural gate  -- robocopy /L : must report nothing to copy from Q -> H
                             (exit bit 0x1 clear). H extras (output union) are fine.
      2. Content proof    -- SHA-256 every file on both sides, compare by relative path.
                             PASS iff every Q file exists on H with an identical hash.

    A folder that PASSES is appended to logs\h_migration_passed_<date>.txt.
    Deletion is a SEPARATE step -- this script never deletes anything.

    Usage:  powershell -File verify_h_migration.ps1 -Folders auto_sorted,output,...
#>
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Folders,
    [string]$Date = '20260722'
)

$ErrorActionPreference = 'Continue'
$q   = 'Q:\Development\image_grid_sorter'
$h   = 'H:\ImageRepository'
$log = "$q\logs\h_migration_verify_$Date.log"
$passedFile = "$q\logs\h_migration_passed_$Date.txt"

function Log($m) {
    $t = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
    Add-Content -Path $log -Value $t
    Write-Host $t
}

# Hashes every file under $base, emitting "<relpath><TAB><sha256>" lines.
$hashBlock = {
    param($base)
    Get-ChildItem -LiteralPath $base -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = $_.FullName.Substring($base.Length).TrimStart('\')
        try   { $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256 -ErrorAction Stop).Hash }
        catch { $hash = 'ERROR' }
        "$rel`t$hash"
    }
}

Log "===== VERIFY RUN START: $($Folders -join ', ') ====="
foreach ($F in $Folders) {
    $qp = Join-Path $q $F
    $hp = Join-Path $h $F
    Log "--- $F : starting ---"
    if (-not (Test-Path -LiteralPath $qp)) { Log "$F : SKIP (not present on Q)"; continue }
    if (-not (Test-Path -LiteralPath $hp)) { Log "$F : FAIL (not present on H) -- NOT cleared"; continue }

    # 1) Structural gate
    robocopy $qp $hp /E /L /NJH /NJS /NDL /NC /NS /FP /R:1 /W:1 | Out-Null
    $structBit = $LASTEXITCODE -band 1   # 0x1 set => Q has files missing/newer on H
    Log "$F : robocopy /L exit=$LASTEXITCODE structBit=$structBit (0 => every Q file already on H)"

    # 2) Content proof -- hash both drives concurrently
    $jq = Start-Job -ScriptBlock $hashBlock -ArgumentList $qp
    $jh = Start-Job -ScriptBlock $hashBlock -ArgumentList $hp
    $qLines = Receive-Job $jq -Wait -AutoRemoveJob
    $hLines = Receive-Job $jh -Wait -AutoRemoveJob

    $hMap = @{}
    foreach ($l in $hLines) {
        $i = $l.LastIndexOf("`t")
        if ($i -gt 0) { $hMap[$l.Substring(0, $i)] = $l.Substring($i + 1) }
    }

    $qCount = 0; $missing = New-Object System.Collections.ArrayList; $mismatch = New-Object System.Collections.ArrayList
    foreach ($l in $qLines) {
        $i = $l.LastIndexOf("`t")
        if ($i -lt 0) { continue }
        $rel = $l.Substring(0, $i); $qh = $l.Substring($i + 1); $qCount++
        if (-not $hMap.ContainsKey($rel)) { [void]$missing.Add($rel) }
        elseif ($qh -eq 'ERROR' -or $hMap[$rel] -eq 'ERROR' -or $hMap[$rel] -ne $qh) { [void]$mismatch.Add($rel) }
    }
    $hCount = $hMap.Count
    Log "$F : Qfiles=$qCount Hfiles=$hCount missingOnH=$($missing.Count) hashMismatch=$($mismatch.Count)"
    foreach ($r in ($missing  | Select-Object -First 25)) { Log "   MISSING : $r" }
    foreach ($r in ($mismatch | Select-Object -First 25)) { Log "   MISMATCH: $r" }

    $pass = ($structBit -eq 0) -and ($missing.Count -eq 0) -and ($mismatch.Count -eq 0)
    if ($pass) {
        Log "$F : PASS -- every Q file present & identical on H (cleared for deletion)"
        Add-Content -Path $passedFile -Value $F
    } else {
        Log "$F : FAIL -- NOT cleared for deletion (left intact on Q)"
    }
}
Log "===== VERIFY RUN DONE ====="
