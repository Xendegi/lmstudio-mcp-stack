param(
    [string]$ScriptContent
)
$bytes = [Text.Encoding]::Unicode.GetBytes($ScriptContent)
$b64 = [Convert]::ToBase64String($bytes)
pwsh -NoProfile -EncodedCommand $b64
