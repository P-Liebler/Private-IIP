[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$BackupRoot,
    [string]$PythonExecutable = (Get-Command python.exe -ErrorAction Stop).Source,
    [string]$DailyTime = '03:00',
    [string]$TaskName = 'PrivateIIP-Backup'
)
$ErrorActionPreference = 'Stop'
$taskRepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskEnvPath = (Resolve-Path -LiteralPath $EnvFile).Path
$taskBackupPath = [System.IO.Path]::GetFullPath($BackupRoot)
$taskScript = Join-Path $taskRepoRoot 'ops\backup.py'
$taskCompose = Join-Path $taskRepoRoot 'docker-compose.prod.yml'
$taskPython = (Resolve-Path -LiteralPath $PythonExecutable).Path
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw 'Task already exists; inspect or remove it explicitly before registering a replacement.'
}
# Task Scheduler launches Python directly; these arguments are not evaluated by a shell.
$taskArguments = '"{0}" --compose-file "{1}" --env-file "{2}" --root "{3}" --prune' -f $taskScript, $taskCompose, $taskEnvPath, $taskBackupPath
$taskAction = New-ScheduledTaskAction -Execute $taskPython -Argument $taskArguments -WorkingDirectory $taskRepoRoot
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
$taskPrincipal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType S4U -RunLevel Limited
if ($PSCmdlet.ShouldProcess($TaskName, 'Register daily private IIP backup')) {
    Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Principal $taskPrincipal | Out-Null
    Write-Output ('Registered daily backup at {0}; destination {1}' -f $DailyTime, $taskBackupPath)
}
