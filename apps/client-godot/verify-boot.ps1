<#
.SYNOPSIS
  Single verification command for the Godot compatibility-boot slice.

    powershell -File apps/client-godot/verify-boot.ps1

  Steps:
    1. locate the pinned Godot executable and the pinned CPython interpreter
       (the interpreter must report 3.9.13)
    2. loopback preconditions: the service port is free and the "unreachable"
       port really has nothing listening
    3. Compatibility API guard baseline, pre-run
    4. Compatibility API unittest discovery + documented loopback smoke
    5. headless hermetic Godot suites: package loader, scene build, fake
       GameApi, boot scene (default scenario), session, game clock,
       camera controls (the loop passes the dead endpoint for the session
       and game-clock suites' failure phase; camera controls ignores it)
    6. boot-scene unreachable-endpoint failure scenario, run with no service
       at all
    7. three live phases against the real Compatibility API: the main-scene
       boot (success, compared with the committed fixture save), the legacy-v0
       GameApi suite, and the structured API-error boot scenario
    8. Compatibility API guard baseline, post-run, must equal the pre-run
       digests
    9. teardown assertions: loopback port released, no working-tree saves/
   10. write apps/client-godot/evidence/boot/boot-report.json

  Exit code 0 only when every assertion holds. Godot / Python output for each
  step is captured under apps/client-godot/.godot/verify-boot/ (ignored).

  The project-scope test is deliberately NOT part of this script: it asserts
  that every allow-listed file, including the evidence this script writes,
  exists in the working tree, so it is run by verify.ps1 after this report has
  been committed.

  Environment: GODOT_EXE and PINNED_PYTHON override discovery; -GodotExe and
  -PythonExe override both. No display session is needed (every engine run is
  headless).
#>
[CmdletBinding()]
param(
    [string]$GodotExe = "",
    [string]$PythonExe = "",
    [int]$Port = 5056,
    [int]$DeadPort = 5057
)

$ErrorActionPreference = "Stop"
$expectedVersion = "4.7.2.stable.official.ed1daf0bf"
$expectedPython = "3.9.13"

# --- locations -------------------------------------------------------------

$projectDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $projectDir)
Push-Location $repoRoot
try {
    $projectRel = "apps/client-godot"
    $bootEvidence = "$projectRel/evidence/boot/boot-report.json"
    $fixtureSaveList = "tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
    $guardBaseline = "tests/fixtures/godot-compatibility-boot/guard-baseline.json"

    $script:failures = New-Object System.Collections.Generic.List[string]
    $script:assertions = New-Object System.Collections.Generic.List[object]
    $script:commands = New-Object System.Collections.Generic.List[object]

    function Report-Result([bool]$Condition, [string]$Message) {
        if ($Condition) {
            Write-Host "[verify-boot] ok   $Message"
        } else {
            Write-Host "[verify-boot] FAIL $Message"
            $script:failures.Add($Message)
        }
        $script:assertions.Add([pscustomobject]@{ name = $Message; ok = [bool]$Condition })
    }
    function Fail([string]$Message) {
        Write-Host "[verify-boot] FAIL $Message"
        $script:failures.Add($Message)
        $script:assertions.Add([pscustomobject]@{ name = $Message; ok = $false })
    }

    # --- locate Godot ------------------------------------------------------

    if ($GodotExe -eq "" -and $env:GODOT_EXE) { $GodotExe = $env:GODOT_EXE }
    if ($GodotExe -eq "") {
        $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
        $candidates = @(Get-ChildItem -Path $wingetRoot -Filter `
            "Godot_v4.7.2-stable_win64.exe" -Recurse -ErrorAction SilentlyContinue)
        if ($candidates.Count -gt 0) {
            $GodotExe = $candidates[0].FullName
            Write-Host "[verify-boot] discovered Godot: $GodotExe"
        }
    }
    if ($GodotExe -eq "" -or -not (Test-Path -LiteralPath $GodotExe)) {
        Write-Host "[verify-boot] FAIL Godot executable not found; pass -GodotExe or set GODOT_EXE"
        exit 2
    }
    $GodotExe = (Resolve-Path -LiteralPath $GodotExe).Path

    # --- locate the pinned interpreter -------------------------------------

    if ($PythonExe -eq "" -and $env:PINNED_PYTHON) { $PythonExe = $env:PINNED_PYTHON }
    if ($PythonExe -eq "") {
        $defaultPython = Join-Path $env:TEMP "opencode\cpython39\pkg\tools\python.exe"
        if (Test-Path -LiteralPath $defaultPython) { $PythonExe = $defaultPython }
    }
    if ($PythonExe -eq "" -or -not (Test-Path -LiteralPath $PythonExe)) {
        Write-Host "[verify-boot] FAIL pinned interpreter not found; pass -PythonExe or set PINNED_PYTHON"
        exit 2
    }
    $PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path

    # --- runner ------------------------------------------------------------

    $logDir = Join-Path $projectDir ".godot/verify-boot"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $script:logIndex = 0

    function Format-Argument([string]$Value) {
        if ($Value -match '[\s"]') { return '"' + ($Value -replace '"', '\"') + '"' }
        return $Value
    }

    function Invoke-Logged {
        param(
            [string]$FileName,
            [string[]]$Arguments,
            [int]$TimeoutSeconds = 900,
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
        $startError = $null

        # System.Diagnostics.Process instead of Start-Process: PowerShell 5.1
        # only exposes a correct ExitCode through -Wait, and this run needs
        # both a reliable exit code and a timeout.
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $FileName
        $startInfo.Arguments = (($Arguments | ForEach-Object { Format-Argument $_ }) -join ' ')
        $startInfo.WorkingDirectory = $repoRoot
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.CreateNoWindow = $true

        try {
            $process = [System.Diagnostics.Process]::Start($startInfo)
        } catch {
            $startError = $_.Exception.Message
            $process = $null
        }
        if ($null -ne $process) {
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
        } else {
            $stderr = "$startError"
        }
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
        $script:commands.Add([pscustomobject]@{
            name = $Name
            command = @($FileName) + @($Arguments)
            exit_code = $exitCode
            timed_out = [bool]$timedOut
            log = "$projectRel/.godot/verify-boot/$([System.IO.Path]::GetFileName($outPath))"
        })
        return [pscustomobject]@{
            ExitCode = $exitCode
            StdOut = $stdout
            StdErr = $stderr
            Combined = $combined
            Log = $base
        }
    }

    function Invoke-Python {
        param(
            [string[]]$Arguments,
            [int]$TimeoutSeconds = 900,
            [string]$Name = "python"
        )
        return Invoke-Logged -FileName $PythonExe -Arguments $Arguments `
            -TimeoutSeconds $TimeoutSeconds -Name $Name
    }

    function Test-PortListening([int]$PortNumber) {
        $client = New-Object Net.Sockets.TcpClient
        try {
            $task = $client.ConnectAsync("127.0.0.1", $PortNumber)
            if ($task.Wait(3000) -and $client.Connected) { return $true }
            return $false
        } catch {
            return $false
        } finally {
            try { $client.Close() } catch { }
        }
    }

    Write-Host "[verify-boot] Godot:   $GodotExe"
    Write-Host "[verify-boot] python:  $PythonExe"
    Write-Host "[verify-boot] service: http://127.0.0.1:$Port (loopback only)"

    # --- 1. interpreter versions -------------------------------------------

    $pyVersion = Invoke-Python -Arguments @("-c", "import sys; print(sys.version.split()[0])") `
        -TimeoutSeconds 120 -Name "python-version"
    $pyVersionText = $pyVersion.StdOut.Trim()
    Report-Result ($pyVersion.ExitCode -eq 0 -and $pyVersionText -eq $expectedPython) `
        "pinned interpreter is CPython $expectedPython (got '$pyVersionText')"

    $godotVersion = Invoke-Logged -FileName $GodotExe -Arguments @("--version") `
        -TimeoutSeconds 120 -Name "godot-version"
    Report-Result ($godotVersion.StdOut -match [regex]::Escape($expectedVersion)) `
        "engine version is $expectedVersion (got: $($godotVersion.StdOut.Trim()))"

    # --- 2. loopback preconditions -----------------------------------------

    Report-Result (-not (Test-PortListening $Port)) `
        "service port $Port is free before the run"
    Report-Result (-not (Test-PortListening $DeadPort)) `
        "unreachable port $DeadPort has nothing listening"

    # --- 3. guard baseline, pre-run ----------------------------------------

    $guardPre = Invoke-Python -Arguments @("-B", "apps/compat-api/guard_baseline.py", "verify") `
        -TimeoutSeconds 600 -Name "guard-pre"
    Report-Result ($guardPre.ExitCode -eq 0) `
        "guard baseline verify exits 0 before the run (got $($guardPre.ExitCode))"
    $guardCombined = ""
    if ($guardPre.Combined -match "combined ([0-9a-f]{64})") { $guardCombined = $Matches[1] }
    Report-Result ($guardCombined -ne "") "guard baseline reports a combined digest"
    $preGuard = $guardCombined

    # --- 4. Compatibility API checks ---------------------------------------

    $compatTests = Invoke-Python -Arguments @(
        "-B", "-m", "unittest", "discover", "-s", "apps/compat-api/tests",
        "-p", "test_*.py", "-v"
    ) -TimeoutSeconds 900 -Name "compat-unittests"
    Report-Result ($compatTests.ExitCode -eq 0) `
        "compat unittest discovery exits 0 (got $($compatTests.ExitCode))"
    Report-Result ($compatTests.Combined -match "(?m)^OK\s*$") `
        "compat unittest discovery reports OK"

    $compatSmoke = Invoke-Python -Arguments @("-B", "apps/compat-api/tests/smoke_loopback.py") `
        -TimeoutSeconds 900 -Name "compat-smoke"
    Report-Result ($compatSmoke.ExitCode -eq 0) `
        "compat loopback smoke exits 0 (got $($compatSmoke.ExitCode))"
    Report-Result ($compatSmoke.Combined -match "SMOKE RESULT: PASS") `
        "compat loopback smoke reports PASS"

    # --- 5. hermetic Godot suites ------------------------------------------

    $hermetic = @("test_package_loader", "test_scene_build", "test_game_api_fake", "test_boot_scene", "test_session", "test_game_clock", "test_camera_controls")
    foreach ($suite in $hermetic) {
        # The dead endpoint is passed to every suite: test_session and
        # test_game_clock read it (their follow-up failing boot replaces a
        # previously active session / clears a previous clock anchor), and
        # suites that ignore user args are unaffected.
        $run = Invoke-Logged -FileName $GodotExe -Arguments @(
            "--headless", "--path", $projectRel,
            "--script", "res://tests/$suite.gd",
            "--", "--gameapi-endpoint=http://127.0.0.1:$DeadPort"
        ) -TimeoutSeconds 900 -Name $suite
        Report-Result ($run.ExitCode -eq 0) "$suite exits 0 (got $($run.ExitCode))"
        Report-Result ($run.Combined -match "\[test\] PASS") "$suite reports PASS"
    }

    # --- 6. unreachable-endpoint failure scenario (no service) -------------

    $unreachable = Invoke-Logged -FileName $GodotExe -Arguments @(
        "--headless", "--path", $projectRel,
        "--script", "res://tests/test_boot_scene.gd",
        "--", "--scenario=unreachable",
        "--gameapi=legacy_v0",
        "--gameapi-endpoint=http://127.0.0.1:$DeadPort"
    ) -TimeoutSeconds 600 -Name "boot-unreachable"
    # The suite exits 0 precisely when it OBSERVED the documented error state
    # (a failing check, i.e. the scene not showing the error, exits 1).
    Report-Result ($unreachable.ExitCode -eq 0) `
        "unreachable scenario exits 0 (got $($unreachable.ExitCode))"
    Report-Result ($unreachable.Combined -match "\[boot\] state=error code=unreachable_endpoint") `
        "unreachable scenario reaches the explicit error state"
    Report-Result ($unreachable.Combined -match "\[test\] PASS script=res://tests/test_boot_scene.gd") `
        "unreachable scenario asserts the error state"
    Report-Result ($unreachable.Combined -notmatch "UNEXPECTED-ACCEPT") `
        "unreachable scenario was asserted, not silently accepted"

    # --- 7. live phases ----------------------------------------------------

    $endpoint = "http://127.0.0.1:$Port"
    $livePhases = @(
        @{
            Name = "boot-main-live"
            Assertions = "main-scene boot success"
            Arguments = @(
                "--headless", "--path", $projectRel, "--",
                "--gameapi=legacy_v0", "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "gameapi-live"
            Assertions = "legacy-v0 GameApi suite"
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_game_api_live.gd",
                "--", "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "boot-api-error-live"
            Assertions = "structured API-error boot scenario"
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_boot_scene.gd",
                "--", "--scenario=api-error",
                "--gameapi=legacy_v0", "--gameapi-endpoint=$endpoint",
                "--boot-user=does-not-exist-0000"
            )
        }
    )

    $phaseLogs = @{}
    foreach ($phase in $livePhases) {
        $phaseArgs = @(
            "-B", "apps/client-godot/compat_live_phase.py",
            "--port", "$Port", "--name", $phase.Name, "--",
            $GodotExe
        ) + $phase.Arguments
        $run = Invoke-Python -Arguments $phaseArgs -TimeoutSeconds 900 -Name $phase.Name
        $phaseLogs[$phase.Name] = $run.Combined
        Report-Result ($run.ExitCode -eq 0) `
            "$($phase.Assertions): live phase exits 0 (got $($run.ExitCode))"
        $summaryLine = ""
        foreach ($line in ($run.Combined -split "`r?`n")) {
            if ($line.StartsWith("LIVE-PHASE-SUMMARY ")) { $summaryLine = $line }
        }
        $summaryOk = $false
        if ($summaryLine -ne "") {
            try {
                $summary = $summaryLine.Substring("LIVE-PHASE-SUMMARY ".Length) | ConvertFrom-Json
                $summaryOk = ($summary.ok -eq $true -and $summary.godot_exit -eq 0 -and $summary.server_exit -eq 0)
            } catch { $summaryOk = $false }
        }
        Report-Result $summaryOk `
            "$($phase.Assertions): live-phase summary records ok with clean teardown"
    }

    # Main-scene success must show the committed fixture save, not a guess.
    $mainOut = ""
    if ($phaseLogs.ContainsKey("boot-main-live")) { $mainOut = $phaseLogs["boot-main-live"] }
    $stateMatch = [regex]::Match($mainOut, '\[boot\] state=(\w+) engine="([^"]*)" protocol=(\S+) game_version="([^"]*)"')
    $summaryMatch = [regex]::Match($mainOut, '\[boot\] summary user_id=(\S+) name="([^"]*)" level=(\d+) xp=(\d+)')
    Report-Result $stateMatch.Success "main-scene boot printed its state marker"
    if ($stateMatch.Success) {
        Report-Result ($stateMatch.Groups[1].Value -eq "ready") `
            "main-scene boot reached state=ready (got $($stateMatch.Groups[1].Value))"
        Report-Result ($stateMatch.Groups[3].Value -eq "compat-v0") `
            "main-scene boot reported protocol compat-v0"
        Report-Result ($stateMatch.Groups[4].Value -eq "alpha 0.02") `
            "main-scene boot reported game version alpha 0.02"
        Report-Result ($stateMatch.Groups[2].Value -match "4\.7\.2") `
            "main-scene boot reported engine 4.7.2 (got $($stateMatch.Groups[2].Value))"
    }
    Report-Result $summaryMatch.Success "main-scene boot printed its summary marker"
    if ($summaryMatch.Success -and (Test-Path -LiteralPath $fixtureSaveList)) {
        $fixture = Get-Content -LiteralPath $fixtureSaveList -Raw | ConvertFrom-Json
        $expected = $fixture.saves[0]
        Report-Result ($summaryMatch.Groups[1].Value -eq $expected.id) `
            "boot summary user id equals the fixture save id"
        Report-Result ($summaryMatch.Groups[2].Value -eq $expected.name) `
            "boot summary name equals the fixture save name"
        Report-Result ($summaryMatch.Groups[3].Value -eq [string]$expected.level) `
            "boot summary level equals the fixture save level"
        Report-Result ($summaryMatch.Groups[4].Value -eq [string]$expected.xp) `
            "boot summary xp equals the fixture save xp"
    } elseif (-not (Test-Path -LiteralPath $fixtureSaveList)) {
        Fail "fixture save list is missing: $fixtureSaveList"
    }

    # The structured API-error scenario must display the service's own code.
    $apiErrorOut = ""
    if ($phaseLogs.ContainsKey("boot-api-error-live")) {
        $apiErrorOut = $phaseLogs["boot-api-error-live"]
    }
    Report-Result ($apiErrorOut -match "\[boot\] state=error code=unknown_user_id") `
        "structured API-error scenario reaches the explicit error state"
    Report-Result ($apiErrorOut -match "\[test\] PASS script=res://tests/test_boot_scene.gd") `
        "structured API-error scenario asserts the error state"

    # --- 8. guard baseline, post-run ---------------------------------------

    $guardPost = Invoke-Python -Arguments @("-B", "apps/compat-api/guard_baseline.py", "verify") `
        -TimeoutSeconds 600 -Name "guard-post"
    Report-Result ($guardPost.ExitCode -eq 0) `
        "guard baseline verify exits 0 after the run (got $($guardPost.ExitCode))"
    $postGuard = ""
    if ($guardPost.Combined -match "combined ([0-9a-f]{64})") { $postGuard = $Matches[1] }
    Report-Result ($postGuard -eq $preGuard -and $preGuard -ne "") `
        "guarded bytes are identical before and after (pre=$preGuard post=$postGuard)"

    # --- 9. teardown assertions --------------------------------------------

    Report-Result (-not (Test-PortListening $Port)) `
        "service port $Port was released after teardown"
    $workingSaves = Join-Path $repoRoot "saves"
    Report-Result (-not (Test-Path -LiteralPath $workingSaves)) `
        "no working-tree saves/ directory was created"

    # --- 10. evidence ------------------------------------------------------

    $fixtureSha = ""
    if (Test-Path -LiteralPath $fixtureSaveList) {
        $fixtureSha = (Get-FileHash -LiteralPath $fixtureSaveList -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $guardSha = ""
    if (Test-Path -LiteralPath $guardBaseline) {
        $guardSha = (Get-FileHash -LiteralPath $guardBaseline -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $gitCommit = ""
    try {
        # No stderr redirection: under $ErrorActionPreference = "Stop" a
        # redirected native stderr becomes a terminating NativeCommandError.
        $gitCommit = (& git rev-parse HEAD | Select-Object -First 1)
    } catch { $gitCommit = "" }

    $pass = ($script:failures.Count -eq 0)
    $report = [ordered]@{
        schema = "godot-compatibility-boot/verify-boot-v1"
        generated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        environment = [ordered]@{
            engine_executable = $GodotExe
            engine_version = $expectedVersion
            python_executable = $PythonExe
            python_version = $pyVersionText
            git_commit = "$gitCommit"
            display_session = $false
            network = "loopback only (127.0.0.1)"
        }
        service = [ordered]@{
            command = @($PythonExe, "-B", "apps/compat-api/run.py", "--port", "$Port")
            endpoint = $endpoint
            port = $Port
            unreachable_endpoint = "http://127.0.0.1:$DeadPort"
            disposable_corpus = $true
        }
        inputs = [ordered]@{
            fixture_save_list = $fixtureSaveList
            fixture_save_list_sha256 = $fixtureSha
            guard_baseline = $guardBaseline
            guard_baseline_sha256 = $guardSha
        }
        switch = [ordered]@{
            setting = "gameapi/implementation"
            values = @("fake", "legacy_v0")
            endpoint_setting = "gameapi/endpoint"
            runtime_override = @("--gameapi=fake", "--gameapi=legacy_v0", "--gameapi-endpoint=<url>", "--boot-user=<id>")
        }
        commands = @($script:commands.ToArray())
        assertions = @($script:assertions.ToArray())
        guard = [ordered]@{
            pre_combined_sha256 = $preGuard
            post_combined_sha256 = $postGuard
            identical = ($preGuard -eq $postGuard -and $preGuard -ne "")
        }
        failures = @($script:failures.ToArray())
        pass = $pass
        claim_limits = @(
            "read-only bootstrap parity for the fresh-save corpus",
            "not gameplay parity",
            "not authentication security",
            "not progressed-player coverage",
            "no Flash, Ruffle, ActionScript, or browser execution",
            "loopback only; no external network"
        )
    }
    $json = $report | ConvertTo-Json -Depth 24
    $evidenceDir = Join-Path $projectDir "evidence/boot"
    New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $projectDir "evidence/boot/boot-report.json"), $json, `
        (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[verify-boot] wrote $bootEvidence"

    if ($pass) {
        Write-Host "[verify-boot] PASS all checks succeeded; logs in $logDir"
        exit 0
    }
    Write-Host "[verify-boot] FAILED $($script:failures.Count) check(s):"
    foreach ($failure in $script:failures) {
        Write-Host "[verify-boot]   - $failure"
    }
    Write-Host "[verify-boot] logs in $logDir"
    exit 1
} finally {
    Pop-Location
}
