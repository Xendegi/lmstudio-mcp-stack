param(
    [string]$Model = "",
    [string]$Action = "list"  # list, load, unload
)
$headers = @{Authorization = "Bearer sk-lm-rTgbTGyG:DGJ5nhlDtjok9UFuDtMx"}
$base = "http://127.0.0.1:1234"
switch ($Action) {
    "list" {
        $r = Invoke-RestMethod -Uri "$base/api/v1/models" -Headers $headers
        $r.models | Where-Object loaded_instances | ForEach-Object {
            $_.loaded_instances | ForEach-Object {
                Write-Output "LOADED: $($_.id) | ctx=$($_.config.context_length)"
            }
        }
        $r.models | Where-Object { -not $_.loaded_instances } | ForEach-Object {
            Write-Output "AVAIL: $($_.key) | max_ctx=$($_.max_context_length)"
        }
    }
    "load" {
        Invoke-RestMethod -Method POST -Uri "$base/api/v1/models/load" -Headers $headers -Body (@{model=$Model} | ConvertTo-Json) -ContentType "application/json"
        Write-Output "Loading: $Model"
    }
    "unload" {
        Invoke-RestMethod -Method POST -Uri "$base/api/v1/models/unload" -Headers $headers -Body (@{instance_id=$Model} | ConvertTo-Json) -ContentType "application/json"
        Write-Output "Unloading: $Model"
    }
}
