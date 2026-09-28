$ErrorActionPreference = "Stop"

$backendReady = Invoke-RestMethod -Uri "http://localhost:8090/ready"
if ($backendReady.status -ne "ready") {
    throw "Backend is not ready"
}

$orderId = "smoke-$([guid]::NewGuid().ToString('N'))"
$body = @{
    order_id = $orderId
    parent_id = $null
    status = "processed"
    weight = 0.5
    attributes = @{
        sum = 100000
        order_type = "LEGAL_REVIEW"
        subject = "contract"
        vip = $false
        client_msp = "small"
        executor_msp = "legal"
        text = "Проверка договора поставки для сквозного интеграционного теста"
        region = "central"
    }
} | ConvertTo-Json -Depth 5

$bodyBytes = [Text.Encoding]::UTF8.GetBytes($body)
Invoke-RestMethod -Method Post -Uri "http://localhost:8091/api/v1/orders" -ContentType "application/json; charset=utf-8" -Body $bodyBytes | Out-Null

$timeoutSeconds = 180
$deadline = (Get-Date).AddSeconds($timeoutSeconds)
do {
    Start-Sleep -Seconds 2
    $order = Invoke-RestMethod -Uri "http://localhost:8091/api/v1/orders/$orderId"
    if ($order.assigned_executor_id) {
        Write-Host "E2E OK: $orderId -> $($order.assigned_executor_id)"
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "E2E timeout: order $orderId was not assigned in $timeoutSeconds seconds"

