"""Backend de inferência: carrega o artefato de /app/models e oferece predições."""
import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

MODELS_DIR = Path(os.getenv("MODELS_DIR", "/app/models"))

app = FastAPI(title="Previsão XRP/BRL", version="1.0")

# Carregado uma única vez, na inicialização do container
with open(MODELS_DIR / "metadata.json", encoding="utf-8") as f:
    META = json.load(f)

ULTIMA_DATA = date.fromisoformat(META["ultima_data_treino"])

if META["modelo"] == "arima":
    from statsmodels.tsa.arima.model import ARIMAResults
    MODELO = ARIMAResults.load(MODELS_DIR / "arima.pkl")
elif META["modelo"] == "prophet":
    from prophet.serialize import model_from_json
    with open(MODELS_DIR / "prophet.json", encoding="utf-8") as f:
        MODELO = model_from_json(f.read())
else:
    raise RuntimeError(f"Modelo desconhecido em metadata.json: {META['modelo']}")


def prever_log(alvo: date) -> tuple[float, float, float]:
    """Previsão e intervalo de 95% em escala log (os modelos usam o log do preço)."""
    passos = (alvo - ULTIMA_DATA).days
    if META["modelo"] == "arima":
        prev = MODELO.get_forecast(steps=passos)
        media = float(np.asarray(prev.predicted_mean)[-1])
        inf, sup = np.asarray(prev.conf_int(alpha=0.05))[-1]
        return media, float(inf), float(sup)
    linha = MODELO.predict(pd.DataFrame({"ds": [pd.Timestamp(alvo)]})).iloc[0]
    return float(linha["yhat"]), float(linha["yhat_lower"]), float(linha["yhat_upper"])


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelo": META["modelo"],
        "ultima_data_treino": META["ultima_data_treino"],
    }


@app.get("/predict")
def predict(data: date = Query(..., description="Data futura no formato AAAA-MM-DD")):
    passos = (data - ULTIMA_DATA).days
    if passos < 1:
        raise HTTPException(400, f"A data deve ser posterior a {ULTIMA_DATA}.")
    if passos > 90:
        raise HTTPException(400, "Horizonte máximo de 90 dias após o fim do treino.")
    media, inf, sup = prever_log(data)
    return {
        "data": data.isoformat(),
        "preco_previsto_brl": round(float(np.exp(media)), 4),
        "intervalo_95_brl": [round(float(np.exp(inf)), 4), round(float(np.exp(sup)), 4)],
        "modelo": META["modelo"],
        "aviso": "Predição experimental, não é recomendação de investimento.",
    }
