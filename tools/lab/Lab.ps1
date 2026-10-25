param(
    [ValidateSet('Menu','Setup','Start','Status','Stop','Resume','Report','Replay','Restart','Readiness')]
    [string]$Action = 'Menu',
    [string]$Value,
    [string]$Campaign,
    [string]$Distro = 'Ubuntu',
    [string]$WslUser = 'derek',
    [string]$Repo = '/home/derek/cm0102-lab',
    [string]$StateRoot = '/home/derek/.local/share/cm0102-lab',
    [string]$ConfigFile,
    [switch]$Qualification
)
$ErrorActionPreference = 'Stop'
$launcherDir = Join-Path $env:LOCALAPPDATA 'CM0102Lab'
$launcherFile = Join-Path $launcherDir 'launcher.json'
if ($Action -eq 'Setup') {
    $settings = @{ distro=$Distro; user=$WslUser; repo=$Repo; state=$StateRoot }
    New-Item -ItemType Directory -Path $launcherDir -Force | Out-Null
    $settings | ConvertTo-Json | Set-Content -LiteralPath $launcherFile -Encoding UTF8
    $installedScript = Join-Path $launcherDir 'Lab.ps1'
    if ($PSCommandPath -ne $installedScript) {
        Copy-Item -LiteralPath $PSCommandPath -Destination $installedScript -Force
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Lab.cmd') -Destination (Join-Path $launcherDir 'Lab.cmd') -Force
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Hold-Lab.ps1') -Destination (Join-Path $launcherDir 'Hold-Lab.ps1') -Force
    }
    if ($ConfigFile) {
        & wsl.exe -d $Distro -u $WslUser -- /usr/bin/python3 "$Repo/tools/lab/lab.py" --root $StateRoot setup --config $ConfigFile
        if ($LASTEXITCODE -ne 0) { throw 'Private input setup failed. ConfigFile must be a WSL absolute path to JSON; see the runbook.' }
    }
    Write-Host "Launcher settings: $launcherFile"
    Write-Host "Windows entry point: $(Join-Path $launcherDir 'Lab.cmd')"
    Write-Host "Private input configuration: $StateRoot/config.json (inside WSL)"
    exit 0
}
if (-not (Test-Path -LiteralPath $launcherFile)) {
    throw 'Run Lab.cmd Setup once. See docs/runbooks/local-lab.md for the private input configuration.'
}
$settings = Get-Content -Raw -LiteralPath $launcherFile | ConvertFrom-Json
function Invoke-Lab([string[]]$LabArgs) {
    & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 "$($settings.repo)/tools/lab/lab.py" --root $settings.state @LabArgs
    if ($LASTEXITCODE -ne 0) { throw 'Lab command failed. Read the actionable WSL error above; existing results are retained.' }
    if ($LabArgs[0] -in @('start','resume','replay')) {
        $selected = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('campaign_id'))" "$($settings.state)/operator.json"
        if ($LASTEXITCODE -ne 0) { throw 'Cannot find the launched campaign for the WSL lifetime holder.' }
        $holderScript = Join-Path $launcherDir 'Hold-Lab.ps1'
        $holderToken = [guid]::NewGuid().ToString('N')
        $holder = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden -PassThru -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$holderScript+'"'),'-LauncherFile',('"'+$launcherFile+'"'),'-Campaign',$selected.Trim(),'-Token',$holderToken)
        $holderReady = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            $observed = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 -c "import json,sys,pathlib;p=pathlib.Path(sys.argv[1]);print(json.loads(p.read_text()).get('token','') if p.exists() else '')" "$($settings.state)/host/$($selected.Trim()).json"
            if ($LASTEXITCODE -eq 0 -and ([string]$observed).Trim() -eq $holderToken) { $holderReady = $true; break }
            if ($holder.HasExited) { throw 'Windows WSL lifetime holder exited before its ready record. Check configuration and resume the retained campaign.' }
            Start-Sleep -Milliseconds 250
        }
        if (-not $holderReady) { throw 'The detached WSL lifetime holder did not publish its ready token. Stop the campaign and inspect setup.' }
        $holder.Id | Set-Content -LiteralPath (Join-Path $launcherDir 'holder.pid') -Encoding ASCII
        Write-Host "Windows WSL lifetime holder started (PID $($holder.Id)); it exits when the campaign stops or completes."
    }
}
if ($Action -eq 'Menu') {
    while ($true) {
        Write-Host "`nCM0102 local research lab"
        Write-Host '1 Start regression  2 Start synthetic  3 Start squad research'
        Write-Host '4 Status  5 Stop  6 Resume  7 Open report  8 Replay result  0 Exit'
        $selection = Read-Host 'Choose'
        switch ($selection) {
            '1' { Invoke-Lab @('start','regression') }
            '2' { Invoke-Lab @('start','synthetic') }
            '3' { Invoke-Lab @('start','research-squad') }
            '4' { Invoke-Lab @('status') }
            '5' { Invoke-Lab @('stop') }
            '6' { Invoke-Lab @('resume') }
            '7' {
                $report = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 "$($settings.repo)/tools/lab/lab.py" --root $settings.state report
                if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
                $windowsReport = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/wslpath -w $report.Trim()
                if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the report path.' }
                Start-Process -FilePath $windowsReport.Trim()
            }
            '8' { Invoke-Lab @('replay',(Read-Host 'Logical job ID from report')) }
            '0' { exit 0 }
            default { Write-Host 'Choose one of the listed numbers.' }
        }
    }
}
$labArgs = @($Action.ToLowerInvariant())
if ($Value) { $labArgs += $Value }
if ($Campaign) {
    if ($Action -in @('Start','Replay')) { $labArgs += @('--campaign',$Campaign) }
    else { $labArgs += $Campaign }
}
if ($Qualification) {
    if ($Action -ne 'Start') { throw '-Qualification applies only to Start.' }
    $labArgs += @('--qualification-hours','24')
}
if ($Action -eq 'Report') {
    $report = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 "$($settings.repo)/tools/lab/lab.py" --root $settings.state @labArgs
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
    $windowsReport = & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/wslpath -w $report.Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the report path.' }
    Start-Process -FilePath $windowsReport.Trim()
    Write-Host $windowsReport.Trim()
} else {
    Invoke-Lab $labArgs
}
