param(
    [string]$Model = "qwen/qwen3.5-9b",
    [string]$Prompt,
    [string]$System = "You are a helpful assistant. Reply concisely in one sentence.",
    [int]$MaxTokens = 256,
    [float]$Temp = 0.3
)
$body = @{
    messages = @(
        @{role = "system"; content = $System}
        @{role = "user"; content = $Prompt}
    )
    max_tokens = $MaxTokens
    temperature = $Temp
    stream = $false
} | ConvertTo-Json
$headers = @{Authorization = "Bearer sk-lm-rTgbTGyG:DGJ5nhlDtjok9UFuDtMx"}
$r = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:1234/api/v1/chat/completions" -Headers $headers -Body $body -ContentType "application/json"
$r.choices[0].message.content
