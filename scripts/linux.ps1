param(
    [string]$LocalScript,
    [string]$RemotePath = "/tmp/remote_script.sh",
    [switch]$NoCopy
)
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$scp = "C:\Windows\System32\OpenSSH\scp.exe"
$key = "$env:USERPROFILE\.ssh\id_ed25519"
if (-not $NoCopy) {
    & $scp -P 2222 -i $key $LocalScript "hpmaster@192.168.2.120`:$RemotePath" 2>&1 | Out-Null
}
& $ssh -i $key -p 2222 hpmaster@192.168.2.120 "chmod +x $RemotePath 2>/dev/null; bash $RemotePath" 2>&1
