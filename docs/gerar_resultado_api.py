"""Renderiza respostas HTTP registradas por testar_api.ps1; nao simula um terminal."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

pasta = Path('/evidencias')
testes = json.loads((pasta / 'evidencias/testes_http.json').read_text(encoding='utf-8-sig'))
selecionados = testes[:2]
fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 1.65]})
fig.suptitle('Backend Docker | Respostas reais dos testes HTTP', fontsize=18, y=0.97)
for ax, teste in zip(axes, selecionados):
    ax.axis('off')
    texto = f"GET {teste['url']}\nHTTP {teste['status_http']}\n\n" + json.dumps(teste['corpo'], indent=2, ensure_ascii=False)
    ax.text(0.02, 0.97, texto, va='top', fontsize=11, fontfamily='DejaVu Sans Mono', transform=ax.transAxes)
fig.text(0.04, 0.025, 'Fonte: docs/evidencias/testes_http.json | Registro: ' + selecionados[0]['instante'], fontsize=9)
fig.subplots_adjust(top=0.89, bottom=0.07, hspace=0.05)
fig.savefig(pasta / 'img/predicao_backend.png', dpi=160)
print('Gerado: docs/img/predicao_backend.png (respostas HTTP registradas)')
