"""Treina ARIMA e Prophet com o histórico do XRP/BRL, compara e exporta o vencedor.

Roda dentro do container de treino:  docker compose run --rm treino
Pastas (montadas pelo docker-compose):
  /app/data   -> CSV de entrada
  /app/models -> artefato gerado (lido depois pelo container de inferência)
  /app/img    -> gráficos usados como evidência
"""
import json
import logging
import os
import warnings
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem janela: salva os gráficos em arquivo
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json
from statsmodels.tsa.arima.model import ARIMA, ARIMAResults
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

DATA = Path(os.getenv("DATA_DIR", "/app/data"))
MODELS = Path(os.getenv("MODELS_DIR", "/app/models"))
IMG = Path(os.getenv("IMG_DIR", "/app/img"))
CSV = DATA / "xrp_brl_mercadobitcoin.csv"
DIAS_TESTE = 30
MODELS.mkdir(exist_ok=True)
IMG.mkdir(exist_ok=True)


def titulo(texto):
    print(f"\n=== {texto} ===")


def metricas(real, previsto):
    erro = np.asarray(real) - np.asarray(previsto)
    return {"MAE": round(float(np.mean(np.abs(erro))), 4),
            "RMSE": round(float(np.sqrt(np.mean(erro ** 2))), 4)}


def novo_prophet():
    # Sazonalidade anual desligada: 3 anos de dados e uma alta isolada em nov-dez/2024
    # faziam o Prophet prever uma alta falsa em todo fim de ano.
    return Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)


# 1. Dados -------------------------------------------------------------------
titulo("1. Dados")
# Formato brasileiro: data dd.mm.aaaa, vírgula decimal, mais recente primeiro
bruto = pd.read_csv(CSV, encoding="utf-8-sig", dtype=str)
df = pd.DataFrame({
    "date": pd.to_datetime(bruto["Data"], format="%d.%m.%Y"),
    "close": bruto["Último"].str.replace(".", "", regex=False).str.replace(",", ".").astype(float),
}).sort_values("date")
serie = df.set_index("date")["close"].asfreq("D").ffill()
log_serie = np.log(serie)
print(f"{len(serie)} dias, de {serie.index[0].date()} até {serie.index[-1].date()}")
print(f"Datas repetidas: {df['date'].duplicated().sum()}")

serie.plot(figsize=(10, 4), title="XRP/BRL - fechamento diário (Mercado Bitcoin)")
plt.ylabel("R$")
plt.tight_layout()
plt.savefig(IMG / "serie_historica.png", dpi=100)
plt.close()

# 2. Estacionariedade --------------------------------------------------------
titulo("2. Teste ADF (H0: série não estacionária)")
p_nivel = adfuller(log_serie.dropna())[1]
p_dif = adfuller(log_serie.diff().dropna())[1]
print(f"log(preço):        p-valor = {p_nivel:.4f}")
print(f"diferença do log:  p-valor = {p_dif:.4f}")
D = 0 if p_nivel < 0.05 else 1
print(f"d escolhido = {D}")

# 3. Treino e teste ----------------------------------------------------------
titulo("3. Divisão treino/teste")
treino, teste = log_serie.iloc[:-DIAS_TESTE], log_serie.iloc[-DIAS_TESTE:]
preco_real = np.exp(teste)
print(f"Treino até {treino.index[-1].date()} | Teste: {teste.index[0].date()} a {teste.index[-1].date()}")

# 4. ARIMA -------------------------------------------------------------------
titulo("4. ARIMA: busca de p e q pelo menor AIC")
melhor_aic, melhor_ordem = np.inf, None
for p, q in product(range(3), range(3)):
    try:
        aic = ARIMA(treino, order=(p, D, q)).fit().aic
        print(f"ARIMA({p},{D},{q})  AIC = {aic:.1f}")
        if aic < melhor_aic:
            melhor_aic, melhor_ordem = aic, (p, D, q)
    except Exception as e:
        print(f"ARIMA({p},{D},{q}) falhou: {e}")
print(f"Melhor ordem: {melhor_ordem}")
prev_arima = np.exp(np.asarray(ARIMA(treino, order=melhor_ordem).fit().forecast(steps=DIAS_TESTE)))
m_arima = metricas(preco_real, prev_arima)
print(f"ARIMA no teste: {m_arima}")

# 5. Prophet -----------------------------------------------------------------
titulo("5. Prophet")
df_treino = treino.reset_index()
df_treino.columns = ["ds", "y"]
prophet_fit = novo_prophet().fit(df_treino)
prev_prophet = np.exp(prophet_fit.predict(pd.DataFrame({"ds": teste.index}))["yhat"].values)
m_prophet = metricas(preco_real, prev_prophet)
print(f"Prophet no teste: {m_prophet}")

# 6. Comparação --------------------------------------------------------------
titulo("6. Comparação (últimos 30 dias)")
print(pd.DataFrame({"ARIMA": m_arima, "Prophet": m_prophet}).T)
vencedor = "arima" if m_arima["MAE"] <= m_prophet["MAE"] else "prophet"
print(f"Modelo escolhido (menor MAE): {vencedor}")

plt.figure(figsize=(10, 4))
plt.plot(np.exp(treino.iloc[-90:]), label="treino (últimos 90 dias)")
plt.plot(preco_real, label="real (teste)", color="black")
plt.plot(teste.index, prev_arima, "--", label=f"ARIMA{melhor_ordem}")
plt.plot(teste.index, prev_prophet, "--", label="Prophet")
plt.legend()
plt.ylabel("R$")
plt.title("Comparação no período de teste")
plt.tight_layout()
plt.savefig(IMG / "comparacao_teste.png", dpi=100)
plt.close()

# 7. Exportação --------------------------------------------------------------
titulo("7. Retreino com todos os dados e exportação")
for f in ["arima.pkl", "prophet.json"]:
    (MODELS / f).unlink(missing_ok=True)

if vencedor == "arima":
    ARIMA(log_serie, order=melhor_ordem).fit().save(MODELS / "arima.pkl")
else:
    df_full = log_serie.reset_index()
    df_full.columns = ["ds", "y"]
    (MODELS / "prophet.json").write_text(model_to_json(novo_prophet().fit(df_full)), encoding="utf-8")

metadata = {
    "modelo": vencedor,
    "ordem_arima": list(melhor_ordem),
    "escala": "log do preço de fechamento",
    "ultima_data_treino": str(log_serie.index[-1].date()),
    "dias_teste": DIAS_TESTE,
    "metricas_teste_brl": {"arima": m_arima, "prophet": m_prophet},
}
(MODELS / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(metadata, indent=2, ensure_ascii=False))

# 8. Conferência -------------------------------------------------------------
titulo("8. Conferindo se o artefato carrega")
if vencedor == "arima":
    carregado = ARIMAResults.load(MODELS / "arima.pkl")
    amanha = float(np.exp(np.asarray(carregado.forecast(1))[-1]))
else:
    from prophet.serialize import model_from_json
    carregado = model_from_json((MODELS / "prophet.json").read_text(encoding="utf-8"))
    dia = pd.DataFrame({"ds": [log_serie.index[-1] + pd.Timedelta(days=1)]})
    amanha = float(np.exp(carregado.predict(dia)["yhat"].iloc[0]))
print(f"Previsão para o dia seguinte: R$ {amanha:.2f}")
print(f"\nArtefato salvo em {MODELS}: {sorted(p.name for p in MODELS.iterdir())}")
