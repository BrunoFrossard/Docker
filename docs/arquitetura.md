# Arquitetura

Diagrama de sequência UML com os componentes e a troca de dados. O artefato sai do container de treino para a pasta `models/` do projeto, e o `docker-compose.yml` monta essa pasta no container de inferência em `/app/models` (somente leitura). O modelo não é copiado para dentro da imagem: para trocar de modelo basta retreinar e reiniciar o container.

```mermaid
sequenceDiagram
    box Container de treinamento (Docker)
        participant CSV as CSV XRP/BRL
        participant NB as Script de treino (treino.py)
    end
    participant ART as Artefato (./models)
    box Container de inferência (Docker)
        participant API as Backend Python (FastAPI)
    end
    participant CLI as Aplicação cliente

    NB->>CSV: Lê datas e fechamentos
    CSV-->>NB: Série histórica
    NB->>NB: Treina ARIMA e Prophet (log do preço)
    NB->>NB: Compara nos últimos 30 dias (MAE/RMSE)
    NB->>ART: Salva modelo vencedor + metadata.json
    Note over ART,API: docker compose monta ./models em /app/models (somente leitura)
    API->>ART: Carrega o artefato na inicialização
    ART-->>API: Modelo em memória
    CLI->>API: GET /health
    API-->>CLI: 200 {"status": "ok", "modelo": "..."}
    CLI->>API: GET /predict?data=AAAA-MM-DD
    API-->>CLI: 200 {"data": "...", "preco_previsto_brl": ...}
```
