param(
    [string]$RemoteCmd
)
$key = "$env:USERPROFILE\.ssh\id_ed25519"
$result = ssh -i $key -p 2222 hpmaster@192.168.2.120 $RemoteCmd 2>&1
$result
