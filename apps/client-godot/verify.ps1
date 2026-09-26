<#
.SYNOPSIS
  Single verification command for the Godot first-render project.

  powershell -File apps/client-godot/verify.ps1

  Steps:
    1. locate the pinned Godot executable and check its version string
    2. SHA-256 digests of both conversion packages and the guarded manifests
    3. headless loader / scene-build / project-scope tests (must exit 0)
    4. deliberate-failure test scenarios (must exit non-zero AND be detected)
    5. windowed render + capture + compare run (writes the evidence)
    6. comparator self-test on a perturbed reference (must exit non-zero)
    7. headless comparison of the committed capture (must exit 0)
    8. scratch report must equal the committed report (provenance fields
       aside) and must agree with this script's own digests
    9. post-run digests must equal the pre-run digests
   10. no Godot script errors may appear in any log

  Exit code 0 only when every assertion holds. Godot's output for each step
  is captured under apps/client-godot/.godot/verify/logs/ (ignored).

  Environment: GODOT_EXE overrides discovery; -GodotExe overrides both.
  A display session is required for step 5 (see README.md); use
  -SkipWindowed to run the CPU-only steps when no display is available.
#>
[CmdletBinding()]
param(
    [string]$GodotExe = "",
    [switch]$SkipWindowed
)

$ErrorActionPreference = "Stop"
$expectedVersion = "4.7.2.stable.official.ed1daf0bf"

# --- locations -------------------------------------------------------------

$projectDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $projectDir)
Push-Location $repoRoot
try {
    $projectRel = "apps/client-godot"
    $evidenceRel = "$projectRel/evidence/first-render"
    $capturePng = "$evidenceRel/first-render.png"
    $evidenceReport = "$evidenceRel/report.json"
    $scratchReport = "$projectRel/.godot/verify/headless-compare-report.json"
    $selfTestReport = "$projectRel/.godot/verify/self-test-report.json"

    $script:failures = New-Object System.Collections.Generic.List[string]
    function Report-Result([bool]$Condition, [string]$Message) {
        if ($Condition) {
            Write-Host "[verify] ok   $Message"
        } else {
            Write-Host "[verify] FAIL $Message"
            $script:failures.Add($Message)
        }
    }
    function Fail([string]$Message) {
        Write-Host "[verify] FAIL $Message"
        $script:failures.Add($Message)
    }

    # --- locate Godot ------------------------------------------------------

    if ($GodotExe -eq "" -and $env:GODOT_EXE) { $GodotExe = $env:GODOT_EXE }
    if ($GodotExe -eq "") {
        $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
        $candidates = @(Get-ChildItem -Path $wingetRoot -Filter `
            "Godot_v4.7.2-stable_win64.exe" -Recurse -ErrorAction SilentlyContinue)
        if ($candidates.Count -gt 0) {
            $GodotExe = $candidates[0].FullName
            Write-Host "[verify] discovered Godot: $GodotExe"
        }
    }
    if ($GodotExe -eq "" -or -not (Test-Path -LiteralPath $GodotExe)) {
        Write-Host "[verify] FAIL Godot executable not found; pass -GodotExe or set GODOT_EXE"
        exit 2
    }
    $GodotExe = (Resolve-Path -LiteralPath $GodotExe).Path
    Write-Host "[verify] Godot: $GodotExe"

    # --- runner ------------------------------------------------------------

    $logDir = Join-Path $projectDir ".godot/verify/logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $script:logIndex = 0

    function Invoke-Godot {
        param(
            [string[]]$Arguments,
            [int]$TimeoutSeconds = 600,
            [string]$Name = "run"
        )
        $script:logIndex++
        $base = Join-Path $logDir ("{0:d2}-{1}" -f $script:logIndex, $Name)
        $outPath = "$base.out.txt"
        $errPath = "$base.err.txt"
        $stdout = ""
        $stderr = ""
        $exitCode = -1
        $timedOut = $false

        # System.Diagnostics.Process instead of Start-Process: PowerShell
        # 5.1 only exposes a correct ExitCode through -Wait, and this run
        # needs both a reliable exit code and a timeout.
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $GodotExe
        $startInfo.Arguments = ($Arguments -join ' ')
        $startInfo.WorkingDirectory = $repoRoot
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        $process = [System.Diagnostics.Process]::Start($startInfo)
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if ($process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.WaitForExit()
            $exitCode = $process.ExitCode
        } else {
            $timedOut = $true
            try { $process.Kill() } catch { }
            try { $process.WaitForExit(10000) } catch { }
        }
        try { $stdout = $stdoutTask.Result } catch { $stdout = "" }
        try { $stderr = $stderrTask.Result } catch { $stderr = "" }
        if ($null -eq $stdout) { $stdout = "" }
        if ($null -eq $stderr) { $stderr = "" }
        [System.IO.File]::WriteAllText($outPath, $stdout)
        [System.IO.File]::WriteAllText($errPath, $stderr)

        $combined = "$stdout`n$stderr"
        if ($timedOut) {
            Fail "$Name timed out after $TimeoutSeconds s"
            $exitCode = -1
        }
        if ($combined -match "SCRIPT ERROR" -or $combined -match "(?m)^ERROR:") {
            Fail "$Name reported a Godot script error (see $base.*.txt)"
        }
        return [pscustomobject]@{
            ExitCode = $exitCode
            StdOut = $stdout
            StdErr = $stderr
            Combined = $combined
            Log = $base
        }
    }

    # --- digests -----------------------------------------------------------

    function Get-FileSha256([string]$Path) {
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    # Same canonical algorithm as scripts/package_paths.gd::directory_digest:
    # "<file sha256 hex>  <relative posix path>\n" for every file, where the
    # path is relative to the digested directory, in ascending ordinal order
    # of that relative path; SHA-256 of the concatenated UTF-8 bytes.
    function Get-DirectoryDigest([string]$AbsoluteDir, [string]$Label) {
        $map = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::Ordinal)
        foreach ($file in @(Get-ChildItem -LiteralPath $AbsoluteDir -Recurse -File)) {
            $inside = $file.FullName.Substring($AbsoluteDir.Length).TrimStart([char]'\', [char]'/') -replace '\\', '/'
            $map[$inside] = (Get-FileSha256 $file.FullName)
        }
        [string[]]$keys = @($map.Keys)
        [System.Array]::Sort($keys, [System.StringComparer]::Ordinal)
        $sha = [System.Security.Cryptography.SHA256]::Create()
        foreach ($key in $keys) {
            $line = "$($map[$key])  $key`n"
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($line)
            [void]$sha.TransformBlock($bytes, 0, $bytes.Length, $null, 0)
        }
        [void]$sha.TransformFinalBlock((New-Object byte[] 0), 0, 0)
        $digest = -join ($sha.Hash | ForEach-Object { $_.ToString("x2") })
        $sha.Dispose()
        return [pscustomobject]@{ Sha256 = $digest; Files = $keys.Count }
    }

    $packageDirs = @(
        "assets/converted/buildings/0001_house_1_m",
        "assets/converted/units/10033_wild_elephant"
    )
    $manifests = @(
        "tools/asset-registry/conversions.json",
        "tools/asset-registry/inspection.json",
        "tools/asset-registry/image_extraction.json"
    )

    function Get-AllDigests {
        $result = @{ Packages = @{}; Manifests = @{} }
        foreach ($dir in $packageDirs) {
            $digest = Get-DirectoryDigest (Join-Path $repoRoot $dir) $dir
            $result.Packages[$dir] = $digest
        }
        foreach ($manifest in $manifests) {
            $result.Manifests[$manifest] = (Get-FileSha256 (Join-Path $repoRoot $manifest))
        }
        return $result
    }

    # --- 1. engine version -------------------------------------------------

    $versionRun = Invoke-Godot -Arguments @("--version") -TimeoutSeconds 120 -Name "version"
    Report-Result ($versionRun.StdOut -match [regex]::Escape($expectedVersion)) `
        "engine version is $expectedVersion (got: $($versionRun.StdOut.Trim()))"

    # --- 2. pre-run digests ------------------------------------------------

    $pre = Get-AllDigests
    foreach ($dir in $packageDirs) {
        Report-Result ($pre.Packages[$dir].Files -gt 0) `
            "pre-digest $dir covers $($pre.Packages[$dir].Files) files"
    }
    Write-Host "[verify] pre-digest packages:"
    foreach ($dir in $packageDirs) {
        Write-Host "[verify]   $($pre.Packages[$dir].Sha256)  $dir"
    }

    # --- 3. headless tests -------------------------------------------------

    $loaderTest = Invoke-Godot -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://tests/test_package_loader.gd"
    ) -TimeoutSeconds 900 -Name "test-package-loader"
    Report-Result ($loaderTest.ExitCode -eq 0) "loader test exits 0 (got $($loaderTest.ExitCode))"
    Report-Result ($loaderTest.Combined -match "\[test\] PASS") "loader test reports PASS"

    $sceneTest = Invoke-Godot -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://tests/test_scene_build.gd"
    ) -TimeoutSeconds 900 -Name "test-scene-build"
    Report-Result ($sceneTest.ExitCode -eq 0) "scene-build test exits 0 (got $($sceneTest.ExitCode))"
    Report-Result ($sceneTest.Combined -match "\[test\] PASS") "scene-build test reports PASS"

    $scopeTest = Invoke-Godot -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://tests/test_project_scope.gd"
    ) -TimeoutSeconds 900 -Name "test-project-scope"
    Report-Result ($scopeTest.ExitCode -eq 0) "project-scope test exits 0 (got $($scopeTest.ExitCode))"
    Report-Result ($scopeTest.Combined -match "\[test\] PASS") "project-scope test reports PASS"

    # --- 4. deliberate-failure scenarios -----------------------------------

    $scenarios = @("foreign-envelope", "broken-chain", "oracle-tamper")
    foreach ($scenario in $scenarios) {
        $run = Invoke-Godot -Arguments @(
            "--headless", "--path", $projectRel,
            "--script", "res://tests/test_package_loader.gd",
            "--", "--scenario=$scenario"
        ) -TimeoutSeconds 900 -Name "scenario-$scenario"
        Report-Result ($run.ExitCode -ne 0) `
            "scenario '$scenario' exits non-zero (got $($run.ExitCode))"
        Report-Result ($run.Combined -match "EXPECTED-FAILURE") `
            "scenario '$scenario' reports the expected rejection"
        Report-Result ($run.Combined -notmatch "UNEXPECTED-ACCEPT") `
            "scenario '$scenario' was rejected, not silently accepted"
    }

    # --- 5. windowed render + capture + compare ----------------------------

    if ($SkipWindowed) {
        Write-Host "[verify] SKIP windowed capture run (-SkipWindowed): needs a display session"
        Fail "capture step skipped, so this run is NOT a complete verification (display session required)"
    } else {
        $windowed = Invoke-Godot -Arguments @("--path", $projectRel) `
            -TimeoutSeconds 900 -Name "windowed-capture"
        Report-Result ($windowed.ExitCode -eq 0) "windowed run exits 0 (got $($windowed.ExitCode))"
        Report-Result (Test-Path -LiteralPath $capturePng) "capture written to $capturePng"
        Report-Result (Test-Path -LiteralPath $evidenceReport) "report written to $evidenceReport"
        if (Test-Path -LiteralPath $capturePng) {
            $pngBytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $capturePng))
            $width = ([int]$pngBytes[16] -shl 24) -bor ([int]$pngBytes[17] -shl 16) `
                -bor ([int]$pngBytes[18] -shl 8) -bor ([int]$pngBytes[19])
            $height = ([int]$pngBytes[20] -shl 24) -bor ([int]$pngBytes[21] -shl 16) `
                -bor ([int]$pngBytes[22] -shl 8) -bor ([int]$pngBytes[23])
            Report-Result ($width -eq 448 -and $height -eq 224) `
                "capture is 448x224 (got ${width}x${height})"
        }
    }

    # --- 6. comparator self-test ------------------------------------------

    $selfTest = Invoke-Godot -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://scripts/run_selftest.gd"
    ) -TimeoutSeconds 900 -Name "comparator-self-test"
    Report-Result ($selfTest.ExitCode -ne 0) `
        "self-test exits non-zero on a perturbed reference (got $($selfTest.ExitCode))"
    Report-Result ($selfTest.Combined -match "\[selftest\] DETECTED") `
        "self-test reports the detected deviation"
    Report-Result (Test-Path -LiteralPath $selfTestReport) `
        "self-test report written to $selfTestReport"
    if (Test-Path -LiteralPath $selfTestReport) {
        $selfReport = Get-Content -LiteralPath $selfTestReport -Raw | ConvertFrom-Json
        $affected = $selfReport.metrics.pixels_over_tolerance
        $deviation = $selfReport.metrics.max_abs_per_channel
        Report-Result ($selfReport.result.pass -eq $false) "self-test report records pass=false"
        Report-Result ($affected -gt 0) "self-test report records affected pixels ($affected)"
        Report-Result ($deviation.r -ge 100) "self-test report records the injected deviation (r=$($deviation.r))"
    }

    # --- 7. headless comparison of the committed capture -------------------

    $compare = Invoke-Godot -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://scripts/run_compare.gd"
    ) -TimeoutSeconds 900 -Name "headless-compare"
    Report-Result ($compare.ExitCode -eq 0) "headless compare exits 0 (got $($compare.ExitCode))"
    Report-Result ($compare.Combined -match "\[compare\] PASS") "headless compare reports PASS"
    Report-Result (Test-Path -LiteralPath $scratchReport) `
        "scratch report written to $scratchReport"

    # --- 8. report consistency --------------------------------------------

    if ((Test-Path -LiteralPath $evidenceReport) -and (Test-Path -LiteralPath $scratchReport)) {
        $committed = Get-Content -LiteralPath $evidenceReport -Raw | ConvertFrom-Json
        $scratch = Get-Content -LiteralPath $scratchReport -Raw | ConvertFrom-Json

        foreach ($document in @($committed, $scratch)) {
            $document.PSObject.Properties.Remove("mode")
            $document.engine.PSObject.Properties.Remove("renderer")
            $document.engine.PSObject.Properties.Remove("video_adapter")
            $document.engine.PSObject.Properties.Remove("video_adapter_api")
        }
        $committedJson = $committed | ConvertTo-Json -Depth 32 -Compress
        $scratchJson = $scratch | ConvertTo-Json -Depth 32 -Compress
        Report-Result ($committedJson -eq $scratchJson) `
            "windowed and headless reports agree (provenance fields aside)"

        $report = Get-Content -LiteralPath $evidenceReport -Raw | ConvertFrom-Json
        Report-Result ($report.result.pass -eq $true) "committed report records pass=true"
        Report-Result (@($report.result.failures).Count -eq 0) "committed report records no failures"
        foreach ($entity in $report.entities) {
            Report-Result ($entity.oracle_ok -eq $true) "oracle holds for $($entity.legacy_id)"
            foreach ($shape in $entity.shapes) {
                Report-Result ($shape.oracle.error_px.x -le 1 -and $shape.oracle.error_px.y -le 1) `
                    "bounds-to-bitmap error within 1 px for $($entity.legacy_id) shape $($shape.character_id)"
            }
        }
        foreach ($entry in $report.inputs.packages) {
            $expected = $pre.Packages[$entry.dir].Sha256
            Report-Result ($entry.directory_sha256 -eq $expected) `
                "report digest matches this script's digest for $($entry.dir)"
        }
        foreach ($entry in $report.inputs.manifests) {
            Report-Result ($entry.sha256 -eq $pre.Manifests[$entry.path]) `
                "report manifest digest matches for $($entry.path)"
        }
        if (Test-Path -LiteralPath $capturePng) {
            $captureSha = Get-FileSha256 (Resolve-Path -LiteralPath $capturePng)
            Report-Result ($report.capture.sha256 -eq $captureSha) `
                "report capture digest matches the committed PNG"
        }
        $ratio = [double]$report.metrics.pixels_over_tolerance_ratio
        $ratioLimit = [double]$report.tolerance.max_pixels_over_tolerance_ratio
        Report-Result ($ratio -le $ratioLimit) `
            "failing-pixel ratio $ratio within tolerance $ratioLimit"
        $coverage = [double]$report.metrics.entity_coverage
        $coverageLimit = [double]$report.tolerance.min_entity_coverage
        Report-Result ($coverage -ge $coverageLimit) `
            "entity coverage $coverage within tolerance $coverageLimit"
        foreach ($channel in @("r", "g", "b", "a")) {
            $mean = [double]$report.metrics.mean_abs_per_channel.$channel
            $meanLimit = [double]$report.tolerance.mean_abs_max
            Report-Result ($mean -le $meanLimit) `
                "mean_abs.$channel $mean within tolerance $meanLimit"
        }
    } else {
        Fail "cannot check report consistency: a report file is missing"
    }

    # --- 9. post-run digests ----------------------------------------------

    $post = Get-AllDigests
    foreach ($dir in $packageDirs) {
        Report-Result ($pre.Packages[$dir].Sha256 -eq $post.Packages[$dir].Sha256) `
            "package bytes unchanged: $dir"
    }
    foreach ($manifest in $manifests) {
        Report-Result ($pre.Manifests[$manifest] -eq $post.Manifests[$manifest]) `
            "manifest bytes unchanged: $manifest"
    }

    # --- summary -----------------------------------------------------------

    if ($script:failures.Count -eq 0) {
        Write-Host "[verify] PASS all checks succeeded; logs in $logDir"
        exit 0
    }
    Write-Host "[verify] FAILED $($script:failures.Count) check(s):"
    foreach ($failure in $script:failures) {
        Write-Host "[verify]   - $failure"
    }
    Write-Host "[verify] logs in $logDir"
    exit 1
} finally {
    Pop-Location
}
