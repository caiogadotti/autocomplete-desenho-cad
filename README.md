<div align="center">

# Autocomplete de Desenho para CAD

Ferramenta de auxílio a desenho para CAD. Você desenha um lado da peça e o
sistema sugere como ela provavelmente termina, comparando com o que você
já desenhou antes ou com um catálogo de referência. Lê e escreve DXF de
verdade, então dá pra abrir o resultado em qualquer CAD.

Não é feita pra um material específico. O corte de rolo de tecido que
aparece no README é só o domínio que usei pra testar se a ideia funciona
com números reais, não o propósito do projeto.

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

Pra saber se isso funciona de verdade e não só "parece bom no README",
precisava de um problema real pra testar. Usei o nesting de corte: pegar
peça retangular e encaixar no rolo de tecido gastando o mínimo possível.
É o *cutting stock problem*, NP-difícil, tem literatura e dá pra medir
aproveitamento e comparar heurística. Motivo de eu ter escolhido esse
domínio: acompanho corte de TNT na Descartee, então sei como é o problema
na prática. Mas o autocomplete em si (`src/ia/`) não sabe nem precisa
saber que a peça é de tecido, só lida com retângulo e medida.

---

## O problema, formulado

> Entrada: um pedido de produção (lista de peças retangulares, cada uma
> com medida e se pode ou não ser girada) e a largura do rolo de
> matéria-prima. Saída: a posição de cada peça no rolo, minimizando o
> comprimento de rolo consumido.

Corte a partir de rolo aparece em vários materiais: tecido, papel, vinil,
chapa metálica fina, couro sintético. O rolo tem **largura fixa** e
comprimento contínuo, o que muda o objetivo em relação ao bin packing
clássico: não se trata de usar menos chapas, e sim de **desenrolar menos
metro linear**. A faixa vazia que sobra na lateral foi paga junto com o
resto.

Uma restrição comum nesse tipo de material, não do algoritmo em si:
**muito material de rolo tem sentido de fabricação** (fibra do tecido,
veio da chapa, grão do couro). Girar uma peça 90 graus muda como ela
estica ou resiste, então nem toda peça pode ser rotacionada livremente.
Isso está em `Peca.pode_girar` e o validador reprova layout que gire o
que não podia.

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

### O autocomplete em si

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
orientação (no exemplo de tecido, o sentido de fabricação), a peça não é
sugerida girada mesmo que a medida batesse desse jeito.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
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
