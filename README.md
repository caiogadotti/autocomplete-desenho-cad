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

Três formas de entrada pro autocomplete:

- **Traço parcial**: passa a medida do lado já desenhado direto pra
  `sugerir_por_uma_aresta()`.
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
medir. Pra ter números de verdade, precisava de um problema real com
métrica clara, não só a promessa de que devia funcionar. Usei nesting de
corte: pegar peça retangular e encaixar num rolo de matéria-prima gastando
o mínimo possível. É o *cutting stock problem*, NP-difícil, tem
literatura e dá pra medir aproveitamento e comparar heurística. Escolhi
esse domínio porque acompanho corte de TNT na Descartee e conheço o
problema na prática, mas o autocomplete em si (`src/ia/`) não sabe nem
precisa saber que a peça é de tecido, só lida com retângulo e medida.

> Entrada: um pedido de produção (lista de peças retangulares, cada uma
> com medida e se pode ou não ser girada) e a largura do rolo de
> matéria-prima. Saída: a posição de cada peça no rolo, minimizando o
> comprimento de rolo consumido.

O rolo tem largura fixa e comprimento contínuo, o que muda o objetivo em
relação a bin packing clássico: não é usar menos chapas, é **desenrolar
menos metro linear**. `Peca.pode_girar` modela a restrição de orientação
que motivou o campo no autocomplete: material de rolo costuma ter sentido
de fabricação (fibra, veio, grão), e girar 90 graus muda como a peça
estica ou resiste.

### O validador vem antes das heurísticas

Em nesting, um bug de sobreposição **melhora** a métrica. Se duas peças
ocupam a mesma área do rolo, o aproveitamento calculado sobe, porque a
mesma superfície passa a contar duas peças. O número fica bonito
justamente porque está errado.

Por isso `Layout.validar()` existe antes de qualquer heurística, e nenhum
resultado abaixo foi reportado sem passar por ele. Ele checa sobreposição
par a par, peça fora da largura do rolo, posição negativa e rotação
proibida. É O(n²) e não tenta ser rápido: roda fora do caminho quente,
onde a correção importa mais que o tempo.

### As heurísticas

**Faixa (shelf).** Empilha as peças em prateleiras horizontais. Cada faixa
tem a altura da peça mais alta que entrou nela, e peças novas vão sendo
encostadas à direita até não caber mais. Simples, e desperdiça o vão
vertical: uma faixa aberta por uma peça de 1200mm fica com 1200mm de
altura mesmo que todas as outras dela tenham 300mm. Duas variantes, a que
para na primeira faixa que serve e a que procura a de menor sobra.

**Skyline.** Guarda o contorno superior real do que já foi cortado,
segmento a segmento, como o horizonte de uma cidade. Uma peça pode
assentar em cima de duas peças baixas vizinhas, coisa que a faixa nunca
enxerga. Custa manter e atualizar esse perfil a cada inserção.

### Resultados medidos

5 pedidos por tamanho, gerados com mistura realista de peças do catálogo
(peça pequena aparece muito mais que peça grande, como num kit cirúrgico
real). Rolo de 1600mm. Todos os layouts validados.

| heurística | 50 peças | 200 peças | 500 peças | tempo (500) |
|---|---:|---:|---:|---:|
| Faixa, primeira que serve | **88,3%** | **90,1%** | **90,3%** | 13,7ms |
| Faixa, melhor encaixe | **88,3%** | **90,1%** | **90,3%** | 13,6ms |
| Skyline | 88,0% | 89,8% | 90,1% | **2,8ms** |
| Skyline, penaliza enterrado | 87,7% | 87,6% | 87,7% | 5,0ms |

**Achado 1: a heurística mais esperta não cobra caro, ela é mais barata.**
Skyline roda 5x mais rápido que a faixa no pedido de 500 peças (2,8ms
contra 13,7ms), apesar de manter uma estrutura de dados mais complexa. A
faixa percorre a lista de faixas abertas a cada peça, e essa lista cresce
sem parar (66 faixas num pedido de 200), enquanto o perfil do skyline se
mantém curto porque segmentos vizinhos de mesma altura são fundidos: 3,9
segmentos em média, contra 66 faixas.

**Achado 2: "melhor encaixe" cobra tempo e não entrega nada.** As duas
variantes de faixa dão aproveitamento idêntico nos três tamanhos. Isso
parecia bug; a investigação mostrou que não é. Elas divergem de verdade
(17 de 200 peças em posição diferente), mas o comprimento total coincide
exatamente, porque comprimento = soma das alturas das faixas, e a decisão
de abrir uma faixa nova é idêntica nas duas variantes. Best fit muda só
onde a peça vai dentro das faixas já abertas, nunca quantas faixas
existem. Resolve um problema que não é o gargalo.

**Achado 3: a "melhoria clássica" do skyline piorou o resultado.** A
literatura de bin packing costuma desempatar pela menor área enterrada
(o vão que fica selado embaixo da peça ao assentar sobre o ponto mais
alto do trecho). Implementei, medi em 20 pedidos, e piorou:

| critério de escolha | aproveitamento |
|---|---:|
| menor topo, empate pela esquerda | **89,58%** |
| menor topo, empate por área enterrada | 86,67% |
| área enterrada acima de tudo | 68,28% |

Compactar à esquerda mantém o horizonte como poucas paredes largas (3,9
segmentos em média); perseguir a menor área enterrada espalha peça pelo
rolo e serrilha o perfil (5,6 segmentos). Perfil fragmentado tem mais
degraus estreitos onde nada mais cabe. O padrão do código é o critério que
mediu melhor; o outro continua disponível por parâmetro.

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
| Modelo de peça, rolo e layout (domínio de teste) | **Pronto** |
| Validador de layout | **Pronto** |
| Heurísticas de nesting (faixa x2, skyline) | **Pronto** |
| Benchmark comparativo | **Pronto** |
| Interface de desenho em tempo real (dentro de um CAD) | Planejado |
| Exportação de etiqueta ZPL | Planejado |

---

## Estrutura do projeto

```
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
