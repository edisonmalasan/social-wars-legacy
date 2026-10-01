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
       camera controls, UI foundation, settings, audio manager, and the
       town vertical slice (projection, town state, town HUD, resource
       projection, town scene, selection, placement, purchase, move, sell,
       store, upgrade, construction, collect, expand, xp, no-Flash gate),
       plus the unit-definitions suite (the static committed unit model,
       read through the already-loaded content registry with no endpoint,
       no request, and no mutation) and the unit-instances suite (the
       player-owned unit instance projected out of a save already in hand,
       with its nested garrison, its fail-closed row parse, and the
       committed corpus's asserted zero instances, also with no endpoint,
       no request, and no mutation), and the unit-queues suite (the typed
       read-only production-queue projection and its recorded contracts, with
       the committed executed-legacy push and pop fixture and the two-part
       post-state proof, also with no endpoint, no request, and no mutation),
       and the unit-production suite (the explicit REFUSAL made a capability:
       a readiness projection that reports a queue's presence and start
       instant while stating the legacy server cannot say whether it is ready,
       the five row-entry branches with each item id's source named and
       re-derived from the committed dispatcher, the training-time and
       add_xp_unit refusals, and the acquisition finding, with no endpoint, no
       request, no production mechanism, and no live phase), and the
        unit-collection suite (the committed collection prize with the one-based
        index and its id-0/id-1 alias, the acquisition inventory with exactly one
        content-derived route, both recorded authority gaps, the three refusals,
        and the committed executed-legacy grant into the corpus's empty storage,
        also with no request issued and no committed-corpus mutation)
       (the loop passes the dead endpoint to every suite: the session and
       game-clock suites use it for their failure phase, the placement,
       purchase, move, sell, store, upgrade, construction, collect, and
       expand suites use it for their transport-failure checks, and suites
       that ignore user args are unaffected)
    6. boot-scene unreachable-endpoint failure scenario, run with no service
       at all
    7. fifteen live phases against the real Compatibility API: the main-scene
       boot (success, compared with the committed fixture save), the legacy-v0
       GameApi suite, the structured API-error boot scenario, the
       placement phase (one intent through the v0 placement endpoint with
       the disposable corpus save asserted mutated), the purchase phase
       (one intent through the v0 purchase endpoint with the disposable
       corpus save asserted mutated), the move phase (one intent
       through the v0 move endpoint with the disposable corpus save
       asserted mutated), the sell phase (one intent through the v0
       sell endpoint with the disposable corpus save asserted mutated), and
       the store phase (one intent through the v0 store endpoint with the
       disposable corpus save asserted mutated), the upgrade phase
       (one intent through the v0 upgrade endpoint, whose response must
       reuse the pre-request key and cell, with the disposable corpus save
       asserted mutated), the construction phase (one row walked through
       start, click, and finish through the v0 construction endpoint, each
       response proving its own per-action post-condition, with the
       disposable corpus save asserted mutated), the collect phase
       (one intent through the v0 collect endpoint, whose response must
       prove the value-level post-state (the collection instant moved
       forward and every stored resource changed by exactly the derived
       delta) and whose construction-state refusal must leave the
       refused row's timers untouched, with the disposable corpus save
       asserted mutated), and the expand phase (one intent through the v0
       expand endpoint, whose response must prove the TWO-part post-state
       (the owned ledger grew by exactly the sent id at the end with every
       existing entry unchanged and in order, and every stored resource
       changed by exactly the derived debit) and whose range, duplicate, and
       requirements refusals must each leave the corpus byte-identical,
       with the disposable corpus save asserted mutated), and the level-up
       phase (the committed corpus's OWN already-consistent level-up through the
       v0 level endpoint, which must be refused with the endpoint's own
       level_already_current code, carry no partial payload, and leave the
       corpus byte-identical; this phase deliberately asserts NO save mutation,
       because at 4 experience against level 1 the committed curve's one-based
       reading already places this corpus at level 1, so the endpoint answers
       before the dispatcher runs), and the queue phase (one push and one pop
       through the v0 queue endpoint against the committed corpus's own real
       placed training producer, whose responses must prove the TWO-part
       post-state (the addressed row's bag carries exactly the derived count and
       the stamped instant, then the three-key teardown removed nu, ts, and ui
       together) and that EVERY stored resource is unchanged, with the
       disposable corpus save asserted mutated), and the collection phase
       (one completion through the v0 collection endpoint against the corpus's
       own empty storage and empty collection ledger, whose response must prove
       the content-derived TWO-part post-state (the granted id and quantity
       equal the COMMITTED prize bag, and the ledger grew by exactly one
       appended id) and that EVERY stored resource is unchanged, with the
       disposable corpus save asserted mutated)
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

    $hermetic = @("test_package_loader", "test_scene_build", "test_game_api_fake", "test_boot_scene", "test_session", "test_game_clock", "test_camera_controls", "test_ui_foundation", "test_settings", "test_audio_manager", "test_town_iso", "test_town_state", "test_town_hud", "test_town_resources", "test_town_selection", "test_town_scene", "test_town_placement", "test_town_purchase", "test_town_move", "test_town_sell", "test_town_store", "test_town_upgrade", "test_town_construction", "test_town_collect", "test_town_expand", "test_town_xp", "test_town_gate", "test_unit_definitions", "test_unit_instances", "test_unit_queues", "test_unit_production", "test_unit_collection")
    foreach ($suite in $hermetic) {
        # The dead endpoint is passed to every suite: test_session and
        # test_game_clock read it (their follow-up failing boot replaces a
        # previously active session / clears a previous clock anchor), and
        # test_town_placement / test_town_purchase / test_town_move /
        # test_town_sell / test_town_store / test_town_upgrade /
        # test_town_construction / test_town_collect / test_town_expand /
        # test_town_xp dial
        # it for their transport-failure checks; suites that ignore user
        # args are unaffected — test_town_resources among them, which is
        # hermetic and reads no endpoint at all.
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
        },
        @{
            Name = "placement-live"
            Assertions = "placement live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_placement.gd",
                "--", "--scenario=live-placement",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "purchase-live"
            Assertions = "purchase live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_purchase.gd",
                "--", "--scenario=live-purchase",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "move-live"
            Assertions = "move live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_move.gd",
                "--", "--scenario=live-move",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "sell-live"
            Assertions = "sell live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_sell.gd",
                "--", "--scenario=live-sell",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "store-live"
            Assertions = "store live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_store.gd",
                "--", "--scenario=live-store",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "upgrade-live"
            Assertions = "upgrade live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_upgrade.gd",
                "--", "--scenario=live-upgrade",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "construction-live"
            Assertions = "construction live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_construction.gd",
                "--", "--scenario=live-construction",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "collect-live"
            Assertions = "collect live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_collect.gd",
                "--", "--scenario=live-collect",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            Name = "expand-live"
            Assertions = "expand live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_expand.gd",
                "--", "--scenario=live-expand",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # NO ExpectSaveMutation, and the omission is deliberate. The
            # committed corpus records 4 experience against level 1, and the
            # committed curve's one-based reading places 4 experience at level
            # 1, so the corpus is ALREADY consistent: the endpoint answers
            # level_already_current before the dispatcher runs and no corpus
            # save can change. Asserting a mutation here would either fail
            # honestly or force a different command into this phase and
            # misattribute its evidence. The phase instead proves the refusal,
            # its empty payload, and the corpus's byte-identity; the POSITIVE
            # half of the two-part post-execution proof is covered hermetically
            # by test_town_xp and test_game_api_fake over an in-memory
            # disagreement.
            Name = "level-up-live"
            Assertions = "level-up live phase"
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_town_xp.gd",
                "--", "--scenario=live-level-up",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The queue phase drives BOTH queue commands through the real v0
            # endpoint against the committed corpus's own real placed training
            # producer (id 26 Command Center at map key 1), so the unchanged
            # legacy dispatcher executes both. --expect-save-mutation holds
            # because the push writes the row's attribute bag.
            Name = "queue-live"
            Assertions = "queue live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_unit_queues.gd",
                "--", "--scenario=live-queue",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The collection phase drives ONE completion through the real v0
            # endpoint against the corpus's own EMPTY storage and EMPTY
            # collection ledger, so the unchanged legacy dispatcher writes the
            # COMMITTED prize of collection 1 into the storage and appends
            # exactly one id to the ledger. --expect-save-mutation holds
            # because the grant is a real write.
            Name = "collection-live"
            Assertions = "collection live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_unit_collection.gd",
                "--", "--scenario=live-collection",
                "--gameapi-endpoint=$endpoint"
            )
        }
    )

    $phaseLogs = @{}
    foreach ($phase in $livePhases) {
        $phaseArgs = @(
            "-B", "apps/client-godot/compat_live_phase.py",
            "--port", "$Port", "--name", $phase.Name
        )
        if ($phase.ContainsKey("ExpectSaveMutation")) {
            # placement-live, purchase-live, move-live, sell-live, store-live,
            # upgrade-live, construction-live, collect-live, expand-live,
            # queue-live, and collection-live: the harness snapshots the
            # disposable corpus saves before the Godot run and fails unless one
            # changed after.
            $phaseArgs += "--expect-save-mutation"
        }
        $phaseArgs += @("--", $GodotExe) + $phase.Arguments
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

    # The placement live phase must show a typed success through the real
    # endpoint, and the harness must have observed the corpus save change.
    $placeOut = ""
    if ($phaseLogs.ContainsKey("placement-live")) { $placeOut = $phaseLogs["placement-live"] }
    Report-Result ($placeOut -match "\[test\] PASS script=res://tests/test_town_placement\.gd") `
        "placement live phase asserts its scenario"
    Report-Result ($placeOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "placement live phase mutated the disposable corpus save"

    # The purchase live phase must show a typed success through the real
    # endpoint, and the harness must have observed the corpus save change.
    $buyOut = ""
    if ($phaseLogs.ContainsKey("purchase-live")) { $buyOut = $phaseLogs["purchase-live"] }
    Report-Result ($buyOut -match "\[test\] PASS script=res://tests/test_town_purchase\.gd") `
        "purchase live phase asserts its scenario"
    Report-Result ($buyOut -match '\[test\] live-purchase applied item=105 store=\{"105":1\} cash=0') `
        "purchase live phase drove one purchase into storage through the v0 endpoint"
    # The harness's save-mutation check is labelled for the placement phase
    # in compat_live_phase.py; the marker itself is what proves a corpus
    # save changed under the purchase-live phase's --expect-save-mutation.
    Report-Result ($buyOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "purchase live phase mutated the disposable corpus save"

    # The move live phase must show a typed success through the real
    # endpoint, and the harness must have observed the corpus save change.
    $moveOut = ""
    if ($phaseLogs.ContainsKey("move-live")) { $moveOut = $phaseLogs["move-live"] }
    Report-Result ($moveOut -match "\[test\] PASS script=res://tests/test_town_move\.gd") `
        "move live phase asserts its scenario"
    Report-Result ($moveOut -match '\[test\] live-move applied item_index=11 cell=\(58, 47\) xp=4 gold=2000') `
        "move live phase drove one move through the v0 endpoint"
    # As with the purchase phase above, the harness's save-mutation check is
    # labelled for the placement phase; the marker is what proves a corpus
    # save changed under the move-live phase's --expect-save-mutation.
    Report-Result ($moveOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "move live phase mutated the disposable corpus save"

    # The sell live phase must show a typed success through the real
    # endpoint, and the harness must have observed the corpus save change.
    $sellOut = ""
    if ($phaseLogs.ContainsKey("sell-live")) { $sellOut = $phaseLogs["sell-live"] }
    Report-Result ($sellOut -match "\[test\] PASS script=res://tests/test_town_sell\.gd") `
        "sell live phase asserts its scenario"
    Report-Result ($sellOut -match '\[test\] live-sell applied item_index=20 cell=\(41, 48\) xp=4 gold=2000') `
        "sell live phase drove one sale through the v0 endpoint"
    # As with the purchase and move phases above, the harness's
    # save-mutation check is labelled for the placement phase; the marker is
    # what proves a corpus save changed under the sell-live phase's
    # --expect-save-mutation.
    Report-Result ($sellOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "sell live phase mutated the disposable corpus save"

    # The store live phase must show a typed success through the real
    # endpoint, and the harness must have observed the corpus save change.
    $storeOut = ""
    if ($phaseLogs.ContainsKey("store-live")) { $storeOut = $phaseLogs["store-live"] }
    Report-Result ($storeOut -match "\[test\] PASS script=res://tests/test_town_store\.gd") `
        "store live phase asserts its scenario"
    Report-Result ($storeOut -match '\[test\] live-store applied item_index=2 cell=\(53, 39\) xp=4 gold=2000') `
        "store live phase drove one store through the v0 endpoint"
    # As with the purchase, move, and sell phases above, the harness's
    # save-mutation check is labelled for the placement phase; the marker is
    # what proves a corpus save changed under the store-live phase's
    # --expect-save-mutation.
    Report-Result ($storeOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "store live phase mutated the disposable corpus save"

    # The upgrade live phase must show a typed success through the real
    # endpoint — including the REUSED key and cell, the fact this line's
    # endpoint proves — and the harness must have observed the corpus save
    # change.
    $upgradeOut = ""
    if ($phaseLogs.ContainsKey("upgrade-live")) { $upgradeOut = $phaseLogs["upgrade-live"] }
    Report-Result ($upgradeOut -match "\[test\] PASS script=res://tests/test_town_upgrade\.gd") `
        "upgrade live phase asserts its scenario"
    Report-Result ($upgradeOut -match '\[test\] live-upgrade applied item_index=12 cell=\(45, 49\) tier=24') `
        "upgrade live phase drove one upgrade through the v0 endpoint, reusing the pre-request key and cell"
    # As with the purchase, move, sell, and store phases above, the harness's
    # save-mutation check is labelled for the placement phase; the marker is
    # what proves a corpus save changed under the upgrade-live phase's
    # --expect-save-mutation.
    Report-Result ($upgradeOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "upgrade live phase mutated the disposable corpus save"

    # The construction live phase must show a typed success through the real
    # endpoint for each of the three actions — including the per-action
    # post-condition this line's endpoint proves (a start carries the derived
    # countdown, a click a counter of at least one, a completion none) — and
    # the harness must have observed the corpus save change.
    $constructionOut = ""
    if ($phaseLogs.ContainsKey("construction-live")) {
        $constructionOut = $phaseLogs["construction-live"]
    }
    Report-Result ($constructionOut -match "\[test\] PASS script=res://tests/test_town_construction\.gd") `
        "construction live phase asserts its scenario"
    Report-Result ($constructionOut -match '\[test\] live-construction applied item_index=11 cell=\(58, 48\) countdown=5 clicks_consumed=true') `
        "construction live phase drove one row through start, click, and finish through the v0 endpoint"
    # As with the purchase, move, sell, store, and upgrade phases above, the
    # harness's save-mutation check is labelled for the placement phase; the
    # marker is what proves a corpus save changed under the construction-live
    # phase's --expect-save-mutation.
    Report-Result ($constructionOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "construction live phase mutated the disposable corpus save"

    # The collect live phase must show a typed success through the real endpoint
    # — including its VALUE-level post-state proof (the collection instant moved
    # forward and every stored resource moved by exactly the derived delta) and
    # the two-layer construction-state refusal that leaves the refused row's
    # start instant and countdown byte-identical — and the harness must have
    # observed the corpus save change.
    $collectOut = ""
    if ($phaseLogs.ContainsKey("collect-live")) { $collectOut = $phaseLogs["collect-live"] }
    Report-Result ($collectOut -match "\[test\] PASS script=res://tests/test_town_collect\.gd") `
        "collect live phase asserts its scenario"
    Report-Result ($collectOut -match '\[test\] live-collect applied item_index=21 cell=\(\d+, \d+\) tier=3') `
        "collect live phase drove one content-derived collection through the v0 endpoint at the top committed rung"
    # As with the purchase, move, sell, store, upgrade, and construction phases
    # above, the harness's save-mutation check is labelled for the placement
    # phase; the marker is what proves a corpus save changed under the
    # collect-live phase's --expect-save-mutation.
    Report-Result ($collectOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "collect live phase mutated the disposable corpus save"

    # The expand live phase must show a typed success through the real endpoint
    # — including its TWO-part value-level post-state proof (the ledger grew by
    # exactly the sent id at the end with every existing entry unchanged and in
    # order, AND every stored resource changed by exactly the derived debit,
    # which for the free committed row is no change at all) and the guards the
    # executed-legacy probe showed the legacy server lacks (an out-of-range id,
    # a duplicate, and a negative id all answered success there) each leaving
    # the corpus byte-identical — and the harness must have observed the corpus
    # save change.
    $expandOut = ""
    if ($phaseLogs.ContainsKey("expand-live")) { $expandOut = $phaseLogs["expand-live"] }
    Report-Result ($expandOut -match "\[test\] PASS script=res://tests/test_town_expand\.gd") `
        "expand live phase asserts its scenario"
    Report-Result ($expandOut -match '\[test\] live-expand applied expansion_id=0 ledger=\[35,36,45,46,0\] debit=\[0,0,0,0,0,0,0,0\]') `
        "expand live phase drove one expansion through the v0 endpoint at the free committed row, with its two-part post-state proof"
    # As with the purchase, move, sell, store, upgrade, construction, and collect
    # phases above, the harness's save-mutation check is labelled for the
    # placement phase; the marker is what proves a corpus save changed under the
    # expand-live phase's --expect-save-mutation.
    Report-Result ($expandOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "expand live phase mutated the disposable corpus save"

    # The level-up live phase must show the committed corpus's own
    # already-consistent level-up refused BY THE REAL ENDPOINT with its own
    # level_already_current code, carrying no partial payload, and must leave the
    # corpus byte-identical. It deliberately asserts NO save mutation: at 4
    # experience against level 1 the committed curve's one-based reading already
    # places this corpus at level 1, so the endpoint answers before the
    # dispatcher runs and no corpus save can change. The positive half of the
    # two-part post-execution proof is covered hermetically.
    $levelOut = ""
    if ($phaseLogs.ContainsKey("level-up-live")) { $levelOut = $phaseLogs["level-up-live"] }
    Report-Result ($levelOut -match "\[test\] PASS script=res://tests/test_town_xp\.gd") `
        "level-up live phase asserts its scenario"
    Report-Result ($levelOut -match '\[test\] live-level-up applied level=\d+ derived=\d+ xp=\d+ refused=level_already_current resources_unchanged=true') `
        "level-up live phase drove the committed corpus's own level-up through the v0 endpoint and proved the refusal, its empty payload, and the corpus's byte-identity"
    Report-Result ($levelOut -match "save_mutation_checked" ) `
        "level-up live phase summary records the harness's mutation flag (expected false for this phase)"

    # The queue live phase must show a typed success for BOTH queue commands
    # through the real endpoint — including its TWO-part value-level post-state
    # proof (the push's derived count and stamped instant landed in the
    # addressed row's attribute bag, the pop's three-key teardown removed nu,
    # ts, and ui together, AND every stored resource is unchanged, which is what
    # makes the neutral-vector claim non-tautological) and the unknown-key
    # refusal carrying the service's own code with no partial payload — and the
    # harness must have observed the corpus save change.
    $queueOut = ""
    if ($phaseLogs.ContainsKey("queue-live")) { $queueOut = $phaseLogs["queue-live"] }
    Report-Result ($queueOut -match "\[test\] PASS script=res://tests/test_unit_queues\.gd") `
        "queue live phase asserts its scenario"
    Report-Result ($queueOut -match '\[test\] live-queue applied map_key=1 push_count=1 pop_torn_down=true') `
        "queue live phase drove a push and a pop through the v0 endpoint against the committed Command Center, with its two-part post-state proof"
    Report-Result ($queueOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "queue live phase mutated the disposable corpus save"

    # The collection live phase must show a typed success through the real
    # endpoint — including its TWO-part CONTENT-DERIVED value-level post-state
    # proof (the granted id and quantity equal the COMMITTED prize bag, the
    # ledger grew by exactly one appended id, AND every stored resource is
    # unchanged, which is what makes the neutral-vector claim non-tautological)
    # — and the harness must have observed the corpus save change.
    $collectionOut = ""
    if ($phaseLogs.ContainsKey("collection-live")) { $collectionOut = $phaseLogs["collection-live"] }
    Report-Result ($collectionOut -match "\[test\] PASS script=res://tests/test_unit_collection\.gd") `
        "collection live phase asserts its scenario"
    Report-Result ($collectionOut -match '\[test\] live-collection applied collection_id=1 item_id=1085 quantity=1 ledger_appended=true resources_unchanged=true') `
        "collection live phase drove one completion through the v0 endpoint, with its content-derived two-part post-state proof"
    Report-Result ($collectionOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "collection live phase mutated the disposable corpus save"

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
