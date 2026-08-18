<div align="center">

# Otimizador de Corte Industrial

**Quanto de TNT sobra no chão, e como o algoritmo decide isso.**

Motor de nesting 2D para corte de peças retangulares em rolo de matéria-prima,
com heurísticas comparadas de forma medida e um validador que impede número
bonito de layout inválido.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)

`Em desenvolvimento`

**Português** &nbsp;·&nbsp; [English](README.en.md)

</div>

---

## Por que esse projeto

Duas experiências minhas se cruzam aqui. Na Systra passei 6 meses fazendo
desenho técnico em AutoCAD, onde o que existe na tela é geometria com
restrição. Na Descartee, indústria de descartáveis hospitalares, o TNT
chega em rolo e vira avental, campo cirúrgico e touca, e o que sobra
entre uma peça e outra é dinheiro que já foi comprado e virou resíduo.

O problema de decidir **como dispor as peças no rolo** para sobrar o menos
possível é o *cutting stock problem*, NP-difícil. Não existe algoritmo que
ache o ótimo em tempo razoável para um pedido de produção, então a
indústria usa heurística. A pergunta que este projeto responde não é
"qual a melhor disposição", é uma mais honesta: **entre as heurísticas
que existem, qual entrega mais aproveitamento neste tipo de peça, e
quanto ela cobra por isso.**

---

## O problema, formulado

> Entrada: um pedido de produção (lista de peças retangulares, cada uma
> com medida e se pode ou não ser girada) e a largura do rolo de TNT.
> Saída: a posição de cada peça no rolo, minimizando o comprimento de
> rolo consumido.

O rolo tem **largura fixa** (1600mm é comum) e comprimento contínuo. Isso
muda o objetivo em relação ao bin packing clássico: não se trata de usar
menos chapas, e sim de **desenrolar menos metro linear**. A faixa vazia
que sobra na lateral foi paga junto com o resto.

Uma restrição que vem do material, não do algoritmo: **TNT tem sentido de
fabricação.** Girar uma peça 90 graus muda como ela estica e resiste, então
peça de avental que precisa esticar no sentido do corpo não pode ser
rotacionada, enquanto peça de embalagem interna pode. Isso está em
`Peca.pode_girar` e o validador reprova layout que gire o que não podia.

---

## O validador vem antes das heurísticas

Em nesting, um bug de sobreposição **melhora** a métrica. Se duas peças
ocupam a mesma área do rolo, o aproveitamento calculado sobe, porque a
mesma superfície passa a contar duas peças. O número fica bonito
justamente porque está errado.

Por isso `Layout.validar()` existe antes de qualquer heurística, e nenhum
resultado deste README foi reportado sem passar por ele. Ele checa
sobreposição par a par, peça fora da largura do rolo, posição negativa e
rotação proibida. É O(n²) e não tenta ser rápido: roda fora do caminho
quente, onde a correção importa mais que o tempo.

---

## As heurísticas

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

---

## Resultados medidos

5 pedidos por tamanho, gerados com mistura realista de peças do catálogo
(peça pequena aparece muito mais que peça grande, como num kit cirúrgico
real). Rolo de 1600mm. Todos os layouts validados.

| heurística | 50 peças | 200 peças | 500 peças | tempo (500) |
|---|---:|---:|---:|---:|
| Faixa, primeira que serve | **88,3%** | **90,1%** | **90,3%** | 13,7ms |
| Faixa, melhor encaixe | **88,3%** | **90,1%** | **90,3%** | 13,6ms |
| Skyline | 88,0% | 89,8% | 90,1% | **2,8ms** |
| Skyline, penaliza enterrado | 87,7% | 87,6% | 87,7% | 5,0ms |

### Achado 1: a heurística mais esperta não cobra caro, ela é mais barata

Skyline roda **5x mais rápido** que a faixa no pedido de 500 peças (2,8ms
contra 13,7ms), apesar de manter uma estrutura de dados mais complexa. A
razão é que a faixa percorre a lista de faixas abertas a cada peça, e essa
lista cresce sem parar (66 faixas num pedido de 200), enquanto o perfil do
skyline se mantém curto porque segmentos vizinhos de mesma altura são
fundidos: **3,9 segmentos em média**, contra 66 faixas.

O custo por peça do skyline é quase constante; o da faixa cresce com o
tamanho do pedido.

### Achado 2: "melhor encaixe" cobra tempo e não entrega nada

As duas variantes de faixa dão aproveitamento **idêntico** nos três
tamanhos. Isso parecia bug, e a investigação mostrou que não é: elas
realmente divergem (17 de 200 peças em posição diferente), mas o
comprimento final coincide **exatamente**, nas 5 sementes.

A razão é estrutural. No modelo de faixas, o comprimento total é a soma
das alturas das faixas, e uma faixa nova só nasce quando **nenhuma**
faixa existente serve, condição idêntica nas duas variantes. Best fit muda
onde a peça vai *dentro* das faixas já abertas, nunca quantas faixas
existem nem que altura têm. Ele resolve um problema que não é o gargalo.

### Achado 3: a "melhoria clássica" do skyline piorou o resultado

A literatura de bin packing costuma desempatar pela menor área
desperdiçada. No skyline isso seria a área que fica **enterrada** embaixo
da peça: quando ela assenta sobre o ponto mais alto do trecho, o vão sobre
os segmentos mais baixos é selado pelo perfil e ninguém mais ocupa.

Implementei, medi em 20 pedidos, e piorou:

| critério de escolha | aproveitamento |
|---|---:|
| menor topo, empate pela esquerda | **89,58%** |
| menor topo, empate por área enterrada | 86,67% |
| área enterrada acima de tudo | 68,28% |

Quanto mais peso a área enterrada recebe, pior fica. A causa também foi
medida: compactar à esquerda mantém o horizonte como poucas paredes largas
(**3,9 segmentos** em média, 5,2 ao final), enquanto perseguir a menor área
enterrada espalha peça pelo rolo e serrilha o perfil (**5,6 segmentos**, 9,4
ao final). Perfil fragmentado tem mais degraus estreitos onde nada mais
cabe. Economizar o vão de agora custa a superfície boa de depois.

O padrão do código é o critério que mediu melhor, e o outro continua
disponível por parâmetro para o benchmark poder mostrar a diferença em
vez de ela virar comentário.

---

## Rodar

```bash
pip install -r requirements.txt
python scripts/comparar_heuristicas.py
```

---

## Estado atual

| Componente | Status |
|---|---|
| Modelo de peça, rolo e layout | **Pronto** |
| Validador de layout | **Pronto** |
| Heurísticas de faixa (2 variantes) | **Pronto** |
| Heurística skyline | **Pronto** |
| Benchmark comparativo | **Pronto** |
| Extração de peças por visão computacional | **Pronto** |
| Leitura/escrita de DXF (CAD) | **Pronto** |
| Sugestão de fechamento por catálogo (IA) | **Pronto** |
| Visualização do plano de corte | **Pronto** |
| Exportação de etiqueta ZPL | Planejado |
| Interface web | Planejado |

---

## Estrutura do projeto

```
├── src/
│   ├── modelo/
│   │   ├── peca.py           Peca, Rolo, PecaPosicionada e geometria de sobreposição
│   │   ├── layout.py         resultado do corte, métricas e validador
│   │   └── catalogo.py       peças de descartáveis hospitalares, geração de pedido
│   ├── heuristicas/
│   │   ├── faixas.py         shelf: primeira que serve e melhor encaixe
│   │   └── skyline.py        perfil do horizonte, com os dois critérios de escolha
│   ├── visao/
│   │   ├── prancha.py        gera desenho técnico sintético com verdade conhecida
│   │   └── extrator.py       acha peça em desenho via OpenCV clássico
│   ├── cad/
│   │   └── dxf.py            lê/escreve DXF (formato real de CAD, via ezdxf)
│   └── ia/
│       ├── sugestor.py       autocomplete de peça, por uma aresta ou por fechamento
│       └── historico.py      histórico de peças desenhadas, persistido em disco
├── scripts/
│   ├── comparar_heuristicas.py   benchmark medido, com validação
│   ├── avaliar_extrator.py       recall/precisão/erro do extrator de visão
│   ├── otimizar.py               CLI: DXF de peças -> DXF de plano de corte
│   ├── ver_plano.py              renderiza um plano DXF em PNG
│   └── sugerir_rascunho.py       CLI: imagem de rascunho -> peças sugeridas
└── docs/
```

### Autocomplete de desenho assistido por IA

O pedido original era "integração de IA com o CAD, com auxílio de desenho,
aprendendo com o usuário". `src/ia/sugestor.py` é a primeira versão disso,
a mais honesta que dá para validar sem dataset de desenho real: em vez de
só reconhecer produto de catálogo, ele tenta prever o resto de uma peça
**antes dela estar pronta**.

- `sugerir_por_uma_aresta()` é o autocomplete de verdade: o usuário desenhou
  só um lado, a peça ainda não existe, e a função devolve uma lista
  ranqueada de como ela provavelmente termina.
- `sugerir_fechamento()` cobre o caso em que as duas dimensões já foram
  desenhadas (ou extraídas de um rascunho/foto via `src/visao/extrator.py`)
  e a medida bruta precisa virar uma medida exata.

O que faz isso aprender com o usuário, e não só reconhecer produto fixo, é
`src/ia/historico.py`: toda peça desenhada e confirmada é registrada num
histórico persistido em disco, que entra nas duas buscas acima **antes**
do catálogo da fábrica (`src/modelo/catalogo.py`) e vence em caso de
empate. Uma medida que o usuário usa toda semana mas que não é produto de
catálogo passa a ser reconhecida da segunda vez em diante.

Em ambos os casos, respeita `pode_girar`: uma peça cujo sentido de
fabricação do TNT importa não é sugerida numa orientação que ela não pode
assumir de verdade, mesmo que a medida bata com ela girada.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
```

---

## Créditos

**Curso:** Engenharia de Sistemas Ciber-Físicos, PUC-SP

Domínio baseado em experiência profissional: 6 meses na Systra (desenho
técnico em AutoCAD) e trabalho com corte de TNT na Descartee, indústria de
descartáveis hospitalares.

As medidas de peça no catálogo são de ordem de grandeza plausível para o
setor, não dados de produto específico de nenhuma empresa.
