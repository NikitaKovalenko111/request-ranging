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
        $frontendOrder = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/orders/$orderId"
        if ($frontendOrder.id -ne $orderId) {
            throw "Frontend API returned another order"
        }
        if ($frontendOrder.assignedExecutorId -ne $order.assigned_executor_id) {
            throw "Frontend API assignment is not synchronized"
        }
        $dashboard = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dashboard?bucket=minute"
        if ($null -eq $dashboard.summary -or $null -eq $dashboard.executorLoads) {
            throw "Frontend dashboard contract is incomplete"
        }
        $ruleSchema = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/rule-schema"
        if ($ruleSchema.version -ne "1") {
            throw "Frontend rule schema is unavailable"
        }
        Write-Host "E2E OK: $orderId -> $($order.assigned_executor_id); frontend API verified"
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "E2E timeout: order $orderId was not assigned in $timeoutSeconds seconds"

