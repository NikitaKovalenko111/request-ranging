$status = Invoke-RestMethod "http://localhost:8091/api/v1/simulation/status"
$target = $status.orders.total + 4000

$body = @{
    mode = "stream_4k"
    target_orders = $target
    orders_per_hour = 4000
    start_lifecycle = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8091/api/v1/simulation/start" `
  -ContentType "application/json" `
  -Body $body
