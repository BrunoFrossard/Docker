"""Gera uma figura das metricas exportadas pelo treinamento, sem valores fixos.
Uso: docker compose run --rm -v "${PWD}/docs:/evidencias" treino python /evidencias/gerar_metricas.py
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

meta = json.loads(Path('/app/models/metadata.json').read_text(encoding='utf-8'))
metricas = meta['metricas_teste_brl']
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('off')
ax.set_title('XRP/BRL | Metricas do treinamento executado', fontsize=17, pad=22)
tabela = ax.table(
    cellText=[[nome.upper(), f"{valores['MAE']:.4f}", f"{valores['RMSE']:.4f}"] for nome, valores in metricas.items()],
    colLabels=['Modelo', 'MAE (BRL)', 'RMSE (BRL)'],
    loc='center', cellLoc='center', bbox=[0.05, 0.35, 0.9, 0.45],
)
tabela.auto_set_font_size(False)
tabela.set_fontsize(14)
for (linha, coluna), celula in tabela.get_celld().items():
    if linha == 0:
        celula.set_facecolor('#16324f')
        celula.set_text_props(color='white', weight='bold')
ax.text(0.05, 0.19, f"Escolhido pelo menor MAE: {meta['modelo'].upper()} | Janela de avaliacao: {meta['dias_teste']} dias", transform=ax.transAxes, fontsize=12)
ax.text(0.05, 0.08, f"Retreino ate: {meta['ultima_data_treino']} | Fonte: models/metadata.json", transform=ax.transAxes, fontsize=11)
fig.tight_layout()
fig.savefig('/evidencias/img/metricas.png', dpi=160)
print(json.dumps(meta, indent=2, ensure_ascii=False))
print('Figura salva: docs/img/metricas.png')

