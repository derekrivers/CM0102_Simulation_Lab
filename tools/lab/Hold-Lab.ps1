param([Parameter(Mandatory=$true)][string]$LauncherFile,
      [Parameter(Mandatory=$true)][string]$Campaign,
      [Parameter(Mandatory=$true)][string]$Token)
$ErrorActionPreference = 'Stop'
$settings = Get-Content -Raw -LiteralPath $LauncherFile | ConvertFrom-Json
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CmLabPower {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
try {
    # Request system availability only while this finite campaign holder exists.
    # This changes no persisted Windows power policy and does not keep the display on.
    if ([CmLabPower]::SetThreadExecutionState([uint32]2147483649) -eq 0) {
        throw 'Cannot establish the campaign system-awake request.'
    }
    & wsl.exe -d $settings.distro -u $settings.user -- /usr/bin/python3 -B "$($settings.repo)/tools/lab/hold.py" --root $settings.state --campaign $Campaign --token $Token
    $holderExit = $LASTEXITCODE
} finally {
    [void][CmLabPower]::SetThreadExecutionState([uint32]2147483648)
}
exit $holderExit
