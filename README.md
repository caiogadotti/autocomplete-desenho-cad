<div align="center">

# Autocomplete de Desenho para CAD

Ferramenta de auxílio a desenho para CAD. Você desenha um lado da peça e o
sistema sugere como ela provavelmente termina, comparando com o que você
já desenhou antes ou com um catálogo de referência. Lê e escreve DXF de
verdade, então dá pra abrir o resultado em qualquer CAD.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)

`Em desenvolvimento`

**Português** &nbsp;·&nbsp; [English](README.en.md)

</div>

---

## Por que esse projeto

Na Systra passei 6 meses desenhando em AutoCAD. Boa parte do tempo não era
projetar nada novo, era redesenhar peça parecida com outra que eu já tinha
feito, só ajustando a medida. Isso ficou martelando: o CAD sabe o que eu
desenhei antes, por que ele não sugere o resto sozinho?

Não tinha dataset de desenho técnico pronto pra treinar rede neural nisso,
então fiz sem. `src/ia/` guarda um histórico do que já foi desenhado e
compara o traço novo contra ele (e contra um catálogo, se o histórico
ainda estiver vazio). Se bater dentro de uma tolerância, sugere fechar a
peça naquela medida.

---

## O problema, formulado

> Entrada: um traço parcial de um desenho técnico (uma medida conhecida,
> ou um retângulo já fechado extraído de rascunho/foto) e o que já se
> conhece sobre o domínio (histórico de peças desenhadas, catálogo de
> referência). Saída: a medida completa mais provável da peça, ranqueada
> por confiança, respeitando as restrições geométricas daquele domínio.

Desenho técnico não tem dataset público anotado do jeito que dígito
manuscrito ou imagem de objeto têm, então treinar rede neural nisso do
zero não é opção realista pra um projeto de curso. O problema formulado
acima é resolvível sem isso: é busca por proximidade num espaço pequeno
(histórico + catálogo), não classificação.

---

## Como funciona o autocomplete

`src/ia/sugestor.py` tem duas funções, pros dois momentos em que dá pra
sugerir algo:

- `sugerir_por_uma_aresta()`: só um lado foi desenhado, a peça ainda nem
  existe. Devolve uma lista ranqueada de como ela provavelmente vai
  terminar. É esse aqui que é o autocomplete de verdade, sugerindo antes
  do desenho estar pronto.
- `sugerir_fechamento()`: as duas dimensões já foram desenhadas (ou vieram
  de um rascunho/foto via `src/visao/extrator.py`), e a função só ajusta a
  medida bruta pra medida exata mais próxima que já se conhece.

`src/ia/historico.py` guarda toda peça que o usuário desenha e confirma.
Esse histórico entra nas duas buscas acima antes do catálogo fixo
(`src/modelo/catalogo.py`), então se der empate ele vence. É o que faz uma
medida que você desenha toda semana, mesmo sem ser produto de catálogo,
passar a ser reconhecida a partir da segunda vez.

As duas respeitam `pode_girar`: se o domínio tiver alguma restrição de
orientação (no exemplo abaixo, o sentido de fabricação do material), a
peça não é sugerida girada mesmo que a medida batesse desse jeito.

Quatro formas de entrada pro autocomplete:

- **Traço parcial**: passa a medida do lado já desenhado direto pra
  `sugerir_por_uma_aresta()`.
- **Dentro do CAD**: `InitGui.py`/`comandos.py` (raiz do repo) são um
  workbench de verdade do FreeCAD, testado dentro do FreeCAD 1.1.3: aba
  nova com botão de toolbar. Seleciona a aresta na tela, clica, escolhe a
  sugestão, o retângulo é desenhado. Instalação e limitações da v1 em
  [`INSTALL_FREECAD.md`](INSTALL_FREECAD.md).
- **DXF real**: `src/cad/dxf.py` lê/escreve DXF via `ezdxf`, testado indo
  e voltando pelo FreeCAD.
- **Rascunho ou foto**: `src/visao/extrator.py` acha os retângulos num
  desenho à mão ou fotografado via OpenCV clássico (sem rede neural),
  descartando o que não é peça (carimbo, linha de cota, contorno da
  folha). Validado com 100% de recall/precisão em desenho sintético e
  erro sub-pixel de medida.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
```

---

## Domínio usado pra validar: nesting de corte

Autocomplete de desenho é fácil de "parecer que funciona" e difícil de
medir. Pra ter número de verdade, usei um problema real com métrica
clara: encaixar peça retangular num rolo gastando o mínimo de material,
o *cutting stock problem*, NP-difícil. Escolhi esse domínio porque
acompanho corte de TNT na Descartee, mas o autocomplete (`src/ia/`) não
sabe nem precisa saber que a peça é de tecido, só lida com retângulo e
medida.

`Layout.validar()` roda antes de qualquer heurística e reprova
sobreposição, peça fora da largura do rolo e rotação proibida, porque um
bug de sobreposição melhora a métrica de aproveitamento em vez de piorar,
o que faria um erro passar por resultado bom. Duas famílias de
heurística comparadas: faixa (shelf, empilha em prateleiras) e skyline
(guarda o contorno real do que já foi cortado). O achado mais forte:
minimizar a área enterrada sob cada peça, critério padrão na literatura
de bin packing, mediu **pior** (89,6% → 68,3% dependendo da
agressividade), porque fragmenta o perfil em vez de manter poucos
segmentos largos. Detalhes e as outras comparações estão nos comentários
de `src/heuristicas/skyline.py` e no benchmark.

```bash
pip install -r requirements.txt
python scripts/comparar_heuristicas.py
```

---

## Estado atual

| Componente | Status |
|---|---|
| Autocomplete por uma aresta e por fechamento | **Pronto** |
| Histórico de peças desenhadas | **Pronto** |
| Leitura/escrita de DXF (CAD) | **Pronto** |
| Extração de peças por visão computacional | **Pronto** |
| Domínio de teste (nesting de corte), pra validar com número real | **Pronto** |
| Workbench dentro do FreeCAD (aba + botão de toolbar) | **Pronto** (v1) |
| Alinhar sugestão com posição/rotação da aresta original | Planejado |
| Generalizar o autocomplete além de busca exata por distância | Planejado |

---

## Estrutura do projeto

```
├── InitGui.py                     registra o workbench no FreeCAD (precisa ficar na raiz)
├── comandos.py                    comando "sugerir peça pela aresta selecionada"
├── INSTALL_FREECAD.md             como instalar e usar dentro do FreeCAD
├── src/
│   ├── ia/
│   │   ├── sugestor.py       autocomplete de peça, por uma aresta ou por fechamento
│   │   └── historico.py      histórico de peças desenhadas, persistido em disco
│   ├── cad/
│   │   └── dxf.py            lê/escreve DXF (formato real de CAD, via ezdxf)
│   ├── visao/
│   │   ├── prancha.py        gera desenho técnico sintético com verdade conhecida
│   │   └── extrator.py       acha peça em desenho via OpenCV clássico
│   ├── modelo/                (domínio de teste: nesting de corte)
│   │   ├── peca.py           Peca, Rolo, PecaPosicionada e geometria de sobreposição
│   │   ├── layout.py         resultado do corte, métricas e validador
│   │   └── catalogo.py       peças de exemplo, geração de pedido
│   └── heuristicas/            (domínio de teste: nesting de corte)
│       ├── faixas.py         shelf: primeira que serve e melhor encaixe
│       └── skyline.py        perfil do horizonte, com os dois critérios de escolha
├── scripts/
│   ├── sugerir_rascunho.py       CLI: imagem de rascunho -> peças sugeridas
│   ├── otimizar.py               CLI: DXF de peças -> DXF de plano de corte
│   ├── ver_plano.py              renderiza um plano DXF em PNG
│   ├── comparar_heuristicas.py   benchmark medido, com validação
│   └── avaliar_extrator.py       recall/precisão/erro do extrator de visão
└── docs/
```

---

## Créditos

**Curso:** Engenharia de Sistemas Ciber-Físicos, PUC-SP

A ideia veio de 6 meses desenhando em AutoCAD na Systra. O domínio usado
pra testar (nesting de corte de rolo) é baseado no que vejo de corte de
TNT na Descartee, mas isso é só o cenário de teste, a ferramenta não sabe
nem precisa saber que existe tecido.

As medidas do catálogo de exemplo são só ordem de grandeza plausível pro
setor, não dado de produto de nenhuma empresa específica.
