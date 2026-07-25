param(
    [string]$Method,
    [string]$Path,
    [string]$Body = ""
)
$headers = @{Authorization = "Bearer sk-lm-rTgbTGyG:DGJ5nhlDtjok9UFuDtMx"}
$uri = "http://127.0.0.1:1234$Path"
if ($Body) {
    Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $Body -ContentType "application/json"
} else {
    Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
}
