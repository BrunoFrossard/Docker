# Previsão XRP/BRL

Execute os comandos a partir desta pasta, com o Docker Desktop iniciado:

```powershell
cd xrp-previsao
docker compose up --build -d
```

A API fica disponível em http://localhost:8000/docs e o estado do serviço em http://localhost:8000/health.

## Estrutura

- `backend/`: API FastAPI e imagem de inferência.
- `training/`: treinamento, dependências e notebook original.
- `data/`: histórico de preços usado no treinamento.
- `models/`: modelo treinado e metadados carregados pela API.
- `docs/`: arquitetura, guia, imagens, evidências e testes.

## Treinar e testar

```powershell
docker compose run --rm --build treino
docker compose restart inferencia
.\docs\testar_api.ps1
```

O treinamento grava o modelo em `models/` e os gráficos em `docs/img/`.
O histórico incluído termina em 2026-01-02. A API aceita datas posteriores ao fim do histórico, até 90 dias depois; um exemplo válido é http://localhost:8000/predict?data=2026-01-03. Os testes incluídos usam esse histórico.

Para encerrar:

```powershell
docker compose down
```
