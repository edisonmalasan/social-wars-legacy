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
       and the unit-movement suite (the typed read-only placement
       projection reporting cell, orientation, footprint, elevation, and
       velocity strictly as committed content, the movement-command
       inventory recording that `move` is type-agnostic and already
       delivered, the client-writable row instant, and the structural
       anti-invention guard over travel time, path, terrain, occupancy,
       bounds, readiness, interpolation, and animation, also with no
       endpoint, no request, and no mutation), and the unit-animations suite
       (the typed read-only asset-timeline LINKAGE projection reporting the
       recorded labels, their recorded frame positions, the per-sprite recorded
       frame counts, and the recorded rate strictly as recorded, the fail-closed
       absent/unreadable/label-less/malformed asset paths with their recorded
       state intact, the six committed animation fields plus the `animal` flag
       as content only with their zero-consumer statements, the measured
       `max_frame` non-equivalence (2 against 1 against 29) adopted nowhere, the
       63-branch command inventory with its five classified vocabulary matches
       and its zero animation commands, the recorded playback refusals, and the
       structural anti-invention guard over duration, loop, state machine,
       transition, priority, interrupt, timing, trigger, and playback helpers,
       also with no endpoint, no request, and no mutation), and the
       unit-behaviors suite (the typed read-only dead-hero ledger projection
       with both legacy increment gates named and exactly two of them, the
       delete-at-zero rule, the fail-closed absent/non-object/non-string-key/
       non-integer-count paths, the three-door command inventory recording that
       `kill` never reaches the ledger and `sell` reaches it only behind the KILL
       guard and only through the `push_dead_unit` engine helper, all 21
       zero-consumer behavioural fields with their MEASURED occurrence counts
       and measured committed distributions, the offline double's delete-at-zero
       decrement and unvalidated re-placement, and the structural
       anti-invention guard over syringe-cost, damage, attack, defence, hit,
       occupancy, and charge helpers, also with no request over the network and
       no committed-corpus mutation), and the research suite (the typed
       read-only projection of both research tracks and all three counters
       reported verbatim, the re-derived command inventory showing the three
       counters are WRITE-ONLY and that `fast_forward` makes the research
       instant client-writable, the price-discarding refusal with its
       non-tautological no-resource-moved proof, the recorded five refusals, and
       the structural anti-invention guard over price, readiness, completion,
       remaining-time, unlock, and reward helpers, also with no endpoint, no
       request, and no mutation), and the quests suite (the typed read-only
       projection of both quest state records, the re-derived six-branch
       inventory with the completion branch's total absence of mutation, the
       three reproduced legacy type and shape quirks, the REFUSED
       client-dictated destruction count recorded as a divergence rather than
       parity, the unbounded goals growth reproduced rather than closed, and the
       transport guard over per-action addressing keys -- five cross-layer
       defects this suite structurally could not catch and that only the live
       phase guards, also with no endpoint, no request, and no mutation), and
       the tutorial suite (the typed read-only projection of the save-level
       completed_tutorial flag with its two-sided gate mirror, the offline
       evaluation of all three verdicts over the offline double, the deliberate
       strict-int/integer asymmetry between the outgoing step and every incoming
       value, the numeric-tolerant gate-record comparison, the structural
       anti-invention guard over step-count, ratio, remaining, reward, bound,
       un-complete and request-body helpers, the recorded absences, the eight
       committed village saves as the only progressed evidence for the field,
       and the two-round committed executed-legacy capture with its minting
       anchor, also with no endpoint, no request, and no mutation),
       and the stored-item-placement suite (the pure projection and mirror of
       the storage-to-map round trip: the eight row slots read verbatim, the
       content-derived attribute bag, the storage projection, the intent keys
       and the dismissed keys, the four refusals and the two recorded geometry
       gaps, the offline double driven through the committed five-step capture
       with its value-level no-resource-moved proofs, the re-derived dispatcher
       branch and engine helpers, the structural anti-invention guard, the
       tree-wide storage-ownership claim that REPLACED the collection suite's
       now-false whole-tree absence, and the report writer -- also with no
       endpoint, no request, and no mutation),
       (the loop passes the dead endpoint to every suite: the session and
       game-clock suites use it for their failure phase, the placement,
       purchase, move, sell, store, upgrade, construction, collect, and
       expand suites use it for their transport-failure checks, and suites
       that ignore user args are unaffected)
    6. boot-scene unreachable-endpoint failure scenario, run with no service
       at all
    7. twenty-three live phases against the real Compatibility API: the main-scene
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
       disposable corpus save asserted mutated), and the behavior phase
       (one revival through the v0 resurrect endpoint against a disposable
       corpus SEEDED with one resurrectable ledger entry through the service's
       documented opt-in COMPAT_SEED_DEAD_HEROES seam — set for this phase only,
       and a throwaway copy rather than a committed corpus — whose response must
       prove the TWO-part post-state (the revived ledger entry is GONE under the
       delete-at-zero rule, the addressed key's row now records the
       server-derived item id, AND every stored resource is unchanged, which is
       what makes the no-syringe-cost claim non-tautological) and whose two
       named refusals must each carry the endpoint's own code with no partial
       payload, with the disposable corpus save asserted mutated), and the
        research phase (the full step -> cash -> item -> reset cycle on BOTH
        tracks through the v0 research endpoint, whose response must prove the
        two-part post-state -- the derived counter transition AND that EVERY
        stored resource is unchanged -- and whose two named refusals must carry
        the endpoint's own codes with no partial payload, with the disposable
        corpus save asserted mutated), and the quests phase (all SIX quest
        branches through the v0 quest endpoint, including the no-op branch's
        whole-state identity, the STRINGIFIED mission identifier and its wrap,
        the derived rank difficulty, the REFUSED destruction count with every
        placed row byte-identical, AND every stored resource unchanged, plus its
        three named refusals, with the disposable corpus save asserted mutated),
        and the tutorial phase (all THREE verdicts through the v0 tutorial
        endpoint, sent in the only order that reaches all three because the flag
        is checked before the gate -- the declined hole step FIRST -- whose
        response must prove the derived 0 -> 1 transition with exactly one
        changed leaf, both no-op verdicts writing nothing, the same 40 rows
        throughout, and EVERY stored resource unchanged across all three, plus
        its two reachable named refusals carrying the endpoint's own codes and
        a record that the third is structurally unreachable from this typed
        surface, with the disposable corpus save asserted mutated), and the
        stored-placement phase (the FIRST working round trip in this battery,
        driven as seed -> place -> reseed -> sale through the v0 endpoints,
        whose responses must prove the committed prize landed in the corpus's
        empty storage, that the map slot was DERIVED server-side from the
        corpus's own placements (the client never sent one), that the
        attribute bag is EMPTY because the committed prize is a unit, that the
        sale credits NOTHING, and that EVERY stored resource is unchanged
        across all four steps -- plus both reachable named refusals carrying
        the endpoint's own codes with no partial payload, with the disposable
        corpus save asserted mutated), and the combat phase (the FULL set of
        combat-addressed rows driven through the v0 combat endpoint against
        the disposable corpus's own unit rows, whose response must prove the
        committed roster-derived count, that the ledger entry for each DEAD
        unit is gone and its PEER'S is not, and that the client-dictated
        destruction-count refusal cannot be expressed through the delivered
        transport at all -- asserted against the shared module, with the phase
        SAYING that rather than implying the endpoint refused it, with the
        disposable corpus save asserted mutated), and the magic phase (the
        magics counter driven TWICE on purpose, because the committed corpus
        carries `privateState.magics == {}` so the FIRST request necessarily
        takes the absent-identity path where both preserved branches write the
        key at ZERO while the service's derived transition gives ONE -- the
        seventh divergence, which the phase asserts is REPORTED rather than
        asserted away -- while the SECOND request on the same identity is
        present at 0, where BOTH sides give 1 and DO agree, so driving both is
        what makes the divergence visible next to a clean increment), and the
        reward phase (both cursor actions through the v0 reward endpoint,
        whose typed response must prove the TWO-part cursor post-state (each
        response's cursor equals the derived successor and the OTHER cursor is
        unchanged) and the FOUR-part reward post-state (the receipt names its
        schedule, the advanced cursor equals its derived successor, every
        stored resource is unchanged, and the daily receipt is unchanged when
        the weekly action ran), plus a CLIENT-side refusal whose corpus is
        byte-identical afterwards -- with the endpoint's own nine refusals
        recorded as covered by apps/compat-api/tests/test_rewards_endpoint.py
        because NO endpoint refusal is expressible through this typed surface
        -- with the disposable corpus save asserted mutated)
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

    $hermetic = @("test_package_loader", "test_scene_build", "test_game_api_fake", "test_boot_scene", "test_session", "test_game_clock", "test_camera_controls", "test_ui_foundation", "test_settings", "test_audio_manager", "test_town_iso", "test_town_state", "test_town_hud", "test_town_resources", "test_town_selection", "test_town_scene", "test_town_placement", "test_town_purchase", "test_town_move", "test_town_sell", "test_town_store", "test_town_upgrade", "test_town_construction", "test_town_collect", "test_town_expand", "test_town_xp", "test_town_gate", "test_unit_definitions", "test_unit_instances", "test_unit_queues", "test_unit_production", "test_unit_experience", "test_unit_collection", "test_unit_movement", "test_unit_animations", "test_unit_behaviors", "test_research", "test_quests", "test_tutorial", "test_stored_item_placement", "test_mission_vocabulary", "test_combat_actions", "test_damage_magic", "test_rewards", "test_social_state", "test_darts", "test_friends", "test_construction_assist")
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
        # hermetic and reads no endpoint at all. test_unit_experience is in
        # that group too and goes further: it asserts the ABSENCE of a
        # transport operation for the field it projects, so the endpoint is
        # never dialled by it at all.
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
        },
        @{
            # The behavior phase drives ONE revival through the real v0 endpoint.
            #
            # The committed corpus holds NO resurrectable row and an EMPTY
            # ledger, so the endpoint's positive path cannot run against it —
            # and manufacturing a unit row in preserved material is refused.
            # Instead the disposable CORPUS COPY this phase's own harness builds
            # under the system temp root is SEEDED with one resurrectable ledger
            # entry through the service's documented, opt-in
            # COMPAT_SEED_DEAD_HEROES seam, which the service reads once at
            # start-up. The seed is set for THIS phase only and cleared
            # immediately afterwards, so no other phase and no normal run is
            # affected, and the committed corpus and every delivered fixture
            # directory stay byte-identical — which is exactly what the
            # no-manufactured-coverage boundary requires.
            #
            # --expect-save-mutation holds because the revival is a real write:
            # the unchanged legacy dispatcher deletes the ledger entry and
            # re-places the row through engine.map_add_item.
            Name = "behavior-live"
            Assertions = "behavior live phase"
            ExpectSaveMutation = $true
            SeedEnvironment = @{ "COMPAT_SEED_DEAD_HEROES" = "1001=1" }
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_unit_behaviors.gd",
                "--", "--scenario=live-behavior",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The research phase drives one FULL step -> cash -> item -> reset
            # cycle through the real v0 endpoint against the committed corpus's
            # OWN research counters (all three at [0, 0]), so the unchanged
            # legacy dispatcher executes four branches over one track.
            # --expect-save-mutation holds because the step branch writes the
            # track's step counter and research instant.
            #
            # No COMPAT_SEED_* seam is needed and none is used: unlike
            # behavior-live, this line's state is present in the committed corpus
            # as committed, and manufacturing it would be refused.
            Name = "research-live"
            Assertions = "research live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_research.gd",
                "--", "--scenario=live-research",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The quests phase drives ALL SIX quest branches through the real v0
            # endpoint against the committed corpus's OWN quest state (goals 151
            # entries all None, ranks {}, questTimes {}, and a recorded NULL
            # quest-variable map), so the unchanged legacy dispatcher executes
            # every quest branch with NO fabricated player state.
            # --expect-save-mutation holds because five of the six branches write:
            # the progress branch writes the derived pair, the chapter branch
            # stringifies the mission and clears the map, the rank branch writes
            # the derived difficulty, and end_quest writes its quest-time entry.
            # The sixth writes NOTHING AT ALL and its step is asserted to have
            # moved no field, while the REFUSED destruction count is proved to
            # have left all 40 placed rows byte-identical.
            #
            # No COMPAT_SEED_* seam is needed and none is used: this line's state
            # is present in the committed corpus as committed, and manufacturing
            # it would be refused.
            Name = "quests-live"
            Assertions = "quests live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_quests.gd",
                "--", "--scenario=live-quests",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The tutorial phase drives all THREE verdicts over the real v0
            # endpoint, and the ORDER is load-bearing rather than incidental.
            # The endpoint checks the flag BEFORE the gate, so once a tutorial
            # completes every later step answers already_completed and the
            # gate_declined verdict is unreachable for the rest of that save's
            # life. The committed corpus starts at the seed value, so the hole
            # step goes FIRST -- otherwise this phase would silently prove only
            # the third verdict while reading as full coverage.
            #
            # The phase asserts each typed response AND its post-state: the
            # derived 0 -> 1 transition with exactly one changed leaf, both
            # no-op verdicts changing nothing at all, the flag genuinely moving
            # in the SAVE between requests, the same 40 rows throughout, and
            # every stored resource unchanged across all three -- which is
            # non-tautological only because the committed capture's minting
            # anchor round really did move all seven.
            #
            # No COMPAT_SEED_* seam is needed and none is used: the flag is
            # present in the committed corpus as committed, at its seed value.
            Name = "tutorial-live"
            Assertions = "tutorial live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_tutorial.gd",
                "--", "--scenario=live-tutorial",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The stored-placement phase drives the FIRST working round trip of
            # the M8/M9 sequence over the real v0 endpoint, in FOUR steps, and the
            # order is load-bearing rather than incidental:
            #
            #   A  complete_collection(1)   seeds storage with the COMMITTED
            #                                prize {1085: 1} -- the only
            #                                content-derived route there is,
            #                                because the committed corpus's own
            #                                storage is EMPTY
            #   B  place_stored_item(1085) the unchanged legacy dispatcher places
            #                                one row under a SERVER-DERIVED map
            #                                slot and consumes the unit
            #   C  complete_collection(1)   the ledger is NOT idempotent, so the
            #                                SAME completion grants the unit back;
            #                                without this step step D has nothing
            #                                to sell
            #   D  sell_stored_item(1085)   the dispatcher removes the storage
            #                                entry and credits NOTHING
            #
            # --expect-save-mutation holds four times over: every step is a real
            # write, and the phase asserts each typed response, its post-state,
            # and that all seven stored resources are UNCHANGED across every
            # step -- which is what makes this line's free-placement and
            # no-refund claims non-tautological.
            #
            # No COMPAT_SEED_* seam is needed and none is used: the storage,
            # the ledger, and the placements are all present in the committed
            # corpus, and manufacturing any of them would be refused.
            Name = "stored-placement-live"
            Assertions = "stored-placement live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_stored_item_placement.gd",
                "--", "--scenario=live-stored-placement",
                "--gameapi-endpoint=$endpoint"
            )
        },
        @{
            # The combat phase drives ONE `kill` through the real v0 endpoint
            # against the committed corpus's OWN placed row (item 26 at map key
            # 1), so the unchanged legacy dispatcher deletes exactly that one row
            # through the same map_lose_item helper end_attack uses. No
            # COMPAT_SEED_* seam is needed and none is used: the row is present
            # in the committed corpus as committed, and manufacturing one would
            # be refused.
            #
            # --expect-save-mutation holds because the deletion is a real write,
            # and the phase asserts the typed response, that the removed row is
            # exactly the addressed key, that all seven stored resources are
            # UNCHANGED, and that the dead-hero ledger did NOT move -- `kill`
            # never touches it, unlike push_dead_unit.
            #
            # The `resolve` ELIGIBILITY REFUSAL is proved HERE against the real
            # endpoint, with its own named code rather than the client-dictated
            # one, and the after-snapshot then proves it moved nothing. The
            # client-dictated-count refusal cannot be expressed through the
            # delivered transport at all, so it is asserted against the shared
            # module instead -- and the phase states that rather than implying
            # the endpoint refused it.
            #
            # The `resolve` POSITIVE path is deliberately NOT driven here: the
            # committed corpus places only buildings, the phase asserts that
            # (zero unit rows) rather than working around it, and the positive
            # destruction-plus-ledger round trip is exercised hermetically over
            # the committed village documents, which do carry unit rows.
            Name = "combat-live"
            Assertions = "combat live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_combat_actions.gd",
                "--", "--scenario=live-combat",
                "--gameapi-endpoint=$endpoint"
            )
        }
        @{
            # magic-live: M10 line 3 (`damage`).  The delivered surface is the
            # magics counter, and the phase drives it twice on purpose.
            #
            # `tests/saves/fresh-player.json` has `privateState.magics == {}`, so
            # the FIRST request necessarily takes the absent-identity path, where
            # both preserved branches write the key at ZERO while the service's
            # derived transition gives ONE.  That is the seventh divergence, and
            # the phase asserts the disagreement is REPORTED rather than asserted
            # away -- `matches_derived` is false here and that is the correct
            # result.  The SECOND request on the same identity is present at 0, so
            # `min(50, 0 + 1) == 1` for the preserved branch and the derived
            # transition alike, and that one DOES agree.  Driving both is what
            # makes the reported divergence visible next to a clean increment.
            #
            # No COMPAT_SEED_* seam is needed and none is used: this line's state
            # is reachable from the committed corpus with no seeding at all, and
            # both requests mutate the disposable save so the harness's
            # save-mutation assertion has something real to see.
            Name = "magic-live"
            Assertions = "magic live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_damage_magic.gd",
                "--", "--scenario=live-magic",
                "--gameapi-endpoint=$endpoint"
            )
        }
        @{
            # reward-live: M10 line 1 (`rewards`).  The delivered surface is a
            # CURSOR TRANSITION -- two branches, two writes each.
            #
            # Both corpus cursors are 0, so each action's derived successor is 1
            # and no seeding seam is needed or used: this line's state is
            # reachable from the committed corpus with no seeding at all, and
            # BOTH requests mutate the disposable save, so the harness's
            # save-mutation assertion has something real to see.
            #
            # The refusal driven here is CLIENT-side (`invalid_action`).  The
            # envelope declares FIFTEEN named reasons and all fifteen are wired
            # into the route's status table (compat_service.py:1743-1774), of
            # which TWELVE resolve in the recorded pre-write validation order.
            # NOT ONE of them is expressible through this typed surface: the
            # typed builder cannot carry a grant shape and
            # `ACTION_ADDRESSING_KEY` is empty for every reward action.  The
            # phase asserts that emptiness instead of implying coverage, and
            # records that the endpoint's own refusals are covered by
            # apps/compat-api/tests/test_rewards_endpoint.py.
            #
            # Counted by constant REFERENCE, not by literal string: the route
            # spells these as `rewards_envelope.REASON_UNKNOWN_ACTION`, so a
            # literal grep reports zero for `unknown_action` and would understate
            # the count -- the same whole-name-vs-literal census trap this project
            # has hit before.
            Name = "reward-live"
            Assertions = "reward live phase"
            ExpectSaveMutation = $true
            Arguments = @(
                "--headless", "--path", $projectRel,
                "--script", "res://tests/test_rewards.gd",
                "--", "--scenario=live-reward",
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
            # queue-live, collection-live, behavior-live, combat-live,
            # magic-live, and reward-live: the
            # harness
            # snapshots the disposable corpus saves before the Godot run and
            # fails unless one changed after.
            $phaseArgs += "--expect-save-mutation"
        }
        $phaseArgs += @("--", $GodotExe) + $phase.Arguments
        # The seed is set for THIS phase only and cleared immediately after the
        # wrapped command returns, so the disposable corpus the harness builds
        # is seeded while no other phase and no post-run check is affected.
        $seededNames = @()
        if ($phase.ContainsKey("SeedEnvironment")) {
            foreach ($seedEntry in $phase.SeedEnvironment.GetEnumerator()) {
                [Environment]::SetEnvironmentVariable(
                    $seedEntry.Key, $seedEntry.Value, "Process")
                $seededNames += $seedEntry.Key
            }
        }
        try {
            $run = Invoke-Python -Arguments $phaseArgs -TimeoutSeconds 900 -Name $phase.Name
        } finally {
            foreach ($seededName in $seededNames) {
                [Environment]::SetEnvironmentVariable($seededName, $null, "Process")
            }
        }
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

    # The behavior live phase must show a typed success through the real
    # endpoint — including its TWO-part value-level post-state proof (the
    # revived ledger entry is GONE under the delete-at-zero rule, the addressed
    # key's row now records the SERVER-DERIVED item id, AND every stored
    # resource is unchanged, which is what makes the no-syringe-cost claim
    # non-tautological) and its two named refusals carrying the endpoint's own
    # codes with no partial payload — and the harness must have observed the
    # corpus save change.
    $behaviorOut = ""
    if ($phaseLogs.ContainsKey("behavior-live")) {
        $behaviorOut = $phaseLogs["behavior-live"]
    }
    Report-Result ($behaviorOut -match "\[test\] PASS script=res://tests/test_unit_behaviors\.gd") `
        "behavior live phase asserts its scenario"
    Report-Result ($behaviorOut -match '\[test\] live-behavior applied item_id=\d+ map_key=\d+ cell=\(\d+, \d+\) ledger_removed=true resources_unchanged=true') `
        "behavior live phase drove one revival through the v0 endpoint, with its two-part post-state proof"
    Report-Result ($behaviorOut -match "refused=unresolvable_ledger_entry,unresolvable_cell") `
        "behavior live phase proved both named refusals with the endpoint's own codes and no partial payload"
    Report-Result ($behaviorOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "behavior live phase mutated the disposable corpus save"

    # The research live phase must show a typed success for each of the four
    # research branches through the real endpoint — including its value-level
    # post-state proof (the derived step counter, the cash branch's
    # instant-only zeroing with NO consumed cash, the item branch's PAIRED
    # step-and-instant reset, the reset branch's three-counter zeroing, AND every
    # stored resource unchanged, which is what makes the no-price claim
    # non-tautological) and its two named refusals carrying the endpoint's own
    # codes with no partial payload — and the harness must have observed the
    # corpus save change.
    $researchOut = ""
    if ($phaseLogs.ContainsKey("research-live")) {
        $researchOut = $phaseLogs["research-live"]
    }
    Report-Result ($researchOut -match "\[test\] PASS script=res://tests/test_research\.gd") `
        "research live phase asserts its scenario"
    Report-Result ($researchOut -match '\[test\] live-research applied step=1 cash=0 item=1 paired_reset=true reset=0 resources_unchanged=true') `
        "research live phase drove the full step -> cash -> item -> reset cycle through the v0 endpoint, with its value-level post-state proof"
    Report-Result ($researchOut -match "refused=invalid_track,invalid_action") `
        "research live phase proved both named refusals with the endpoint's own codes and no partial payload"
    Report-Result ($researchOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "research live phase mutated the disposable corpus save"

    # The quests live phase must show a typed success for each of the SIX quest
    # branches through the real endpoint — including the no-op branch's
    # whole-state identity, the chapter branch's STRINGIFIED identifier and
    # cleared map, the wrap of an out-of-range identifier, the derived rank
    # difficulty, the REFUSED destruction count with every placed row
    # byte-identical, AND every stored resource unchanged — plus its three named
    # refusals carrying the endpoint's own codes with no partial payload — and
    # the harness must have observed the corpus save change.
    $questsOut = ""
    if ($phaseLogs.ContainsKey("quests-live")) {
        $questsOut = $phaseLogs["quests-live"]
    }
    Report-Result ($questsOut -match "\[test\] PASS script=res://tests/test_quests\.gd") `
        "quests live phase asserts its scenario"
    Report-Result ($questsOut -match '\[test\] live-quests applied progress_pair=\[0, 0\] no_op_wrote=0 quest_var=self_healed mission="5" then wrapped "1" difficulty=1 quest_time_written=true rows_byte_identical=true reward_paid=0 resources_unchanged=true') `
        "quests live phase drove all six branches through the v0 endpoint, with the refused destruction proved byte-identical over the whole placed-row set and its value-level post-state proof"
    Report-Result ($questsOut -match "refused=ignored_quest_var_key,invalid_quest_index,invalid_action" `
            -and $questsOut -match "missing_key_refusals=structurally_unreachable") `
        "quests live phase proved its three named refusals with the endpoint's own codes and no partial payload, and recorded that the five missing-key refusals are structurally unreachable through the typed client"
    Report-Result ($questsOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "quests live phase mutated the disposable corpus save"

    # The tutorial live phase must reach ALL THREE verdicts through the real
    # endpoint — which is only possible in the order it uses, because the flag is
    # checked before the gate — and prove its value-level post-state: the derived
    # 0 -> 1 transition with exactly one changed leaf, both no-ops writing
    # nothing, the same 40 rows throughout, and every stored resource unchanged
    # across all three, plus its three named refusals carrying the endpoint's own
    # codes.
    $tutorialOut = ""
    if ($phaseLogs.ContainsKey("tutorial-live")) {
        $tutorialOut = $phaseLogs["tutorial-live"]
    }
    Report-Result ($tutorialOut -match "\[test\] PASS script=res://tests/test_tutorial\.gd") `
        "tutorial live phase asserts its scenario"
    Report-Result ($tutorialOut -match 'declined=no_op_wrote=0 hole_step=16 arm=none then completed=0->1 changed=1 leaf_flag=true then repeated=no_op_wrote=0 rows=40 resources_unchanged=3') `
        "tutorial live phase drove all three verdicts through the v0 endpoint, with its value-level post-state proof and the same 40 rows throughout"
    Report-Result ($tutorialOut -match "refused=missing_user_id,unknown_user_id invalid_step=structurally_unreachable") `
        "tutorial live phase proved its two reachable refusals with the endpoint's own codes and recorded that the third is unreachable from this typed surface"
    Report-Result ($tutorialOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "tutorial live phase mutated the disposable corpus save"

    # The stored-placement live phase is the first WORKING ROUND TRIP in this
    # battery, so its assertions are about a transaction that must SUCCEED, not
    # about a refusal: the committed prize seeded into storage, a server-DERIVED
    # map slot (the client never sent one), an empty content-derived attribute
    # bag, a sale that credits nothing, both resources-unchanged proofs, and both
    # reachable refusals carrying the endpoint's own codes.
    $storedOut = ""
    if ($phaseLogs.ContainsKey("stored-placement-live")) {
        $storedOut = $phaseLogs["stored-placement-live"]
    }
    Report-Result ($storedOut -match "\[test\] PASS script=res://tests/test_stored_item_placement\.gd") `
        "stored-placement live phase asserts its scenario"
    Report-Result ($storedOut -match '\[test\] live-stored-placement seeded=1 placed_key=\d+ cell=58,47 sold=1085 refund=0 resources_unchanged=true refused=unknown_item_id,not_in_storage') `
        "stored-placement live phase drove seed -> place -> reseed -> sell through the v0 endpoint, with a server-derived map slot, a content-derived bag, no refund, and both reachable refusals"
    Report-Result ($storedOut -match "(?m)^PASS corpus save mutated by the live placement") `
        "stored-placement live phase mutated the disposable corpus save"

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
