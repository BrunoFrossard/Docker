param([string]$BaseUrl = 'http://localhost:8000')
$ErrorActionPreference = 'Stop'
$destino = Join-Path $PSScriptRoot 'evidencias'
New-Item -ItemType Directory -Force $destino | Out-Null
Add-Type -AssemblyName System.Net.Http
$cliente = [System.Net.Http.HttpClient]::new()
$casos = @(
    @{ Nome = 'health'; Rota = '/health'; Status = 200 },
    @{ Nome = 'predicao'; Rota = '/predict?data=2026-01-03'; Status = 200 },
    @{ Nome = 'data_passada'; Rota = '/predict?data=2026-01-02'; Status = 400 },
    @{ Nome = 'horizonte_excedido'; Rota = '/predict?data=2026-10-15'; Status = 400 },
    @{ Nome = 'data_invalida'; Rota = '/predict?data=invalida'; Status = 422 }
)
$registros = @()
try {
    foreach ($caso in $casos) {
        $url = $BaseUrl + $caso.Rota
        $resposta = $cliente.GetAsync($url).GetAwaiter().GetResult()
        $corpo = $resposta.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $status = [int]$resposta.StatusCode
        [System.IO.File]::WriteAllText((Join-Path $destino ($caso.Nome + '.json')), $corpo, [System.Text.UTF8Encoding]::new($false))
        $json = $corpo | ConvertFrom-Json
        Write-Host "`nGET $url`nHTTP $status"
        Write-Host ($json | ConvertTo-Json -Depth 10)
        $registros += [pscustomobject]@{ instante = (Get-Date).ToString('o'); metodo = 'GET'; url = $url; status_http = $status; esperado = $caso.Status; corpo = $json }
        if ($status -ne $caso.Status) { throw "Status inesperado: $status" }
        if ($caso.Nome -eq 'health' -and $json.status -ne 'ok') { throw 'Health sem status ok' }
        if ($caso.Nome -eq 'predicao') {
            if ($json.preco_previsto_brl -le 0) { throw 'Preco deve ser positivo' }
            if ($json.intervalo_95_brl[0] -gt $json.preco_previsto_brl -or $json.intervalo_95_brl[1] -lt $json.preco_previsto_brl) { throw 'Intervalo inconsistente' }
        }
    }
    Write-Host "`nTodos os 5 testes HTTP passaram."
} finally {
    $registros | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 (Join-Path $destino 'testes_http.json')
    $cliente.Dispose()
}
