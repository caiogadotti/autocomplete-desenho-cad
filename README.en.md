<div align="center">

# Industrial Cutting Optimizer

**How much TNT fabric ends up as waste, and how the algorithm decides that.**

2D nesting engine for cutting rectangular pieces from a roll of raw
material, with heuristics compared through measurement and a validator
that stops a pretty number from hiding an invalid layout.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)

`In progress`

[Português](README.md) &nbsp;·&nbsp; **English**

</div>

---

## Why this project

Two of my own experiences meet here. At Systra I spent 6 months doing
technical drawing in AutoCAD, where everything on screen is constrained
geometry. At Descartee, a disposable hospital-supply manufacturer, TNT
fabric arrives on a roll and becomes surgical gowns, drapes, and caps, and
whatever is left between one piece and the next is money already spent
turned into scrap.

Deciding **how to arrange pieces on the roll** to minimize what is left
over is the cutting stock problem, NP-hard. No algorithm finds the optimum
in reasonable time for a real production order, so the industry relies on
heuristics. This project answers a more honest question than "what's the
best layout": **among the heuristics that exist, which one delivers more
usable yield for this kind of piece, and what does it cost to get there.**

---

## The problem, formulated

> Input: a production order (list of rectangular pieces, each with a size
> and whether it can be rotated) and the width of the TNT roll.
> Output: the position of each piece on the roll, minimizing the roll
> length consumed.

The roll has a **fixed width** (1600mm is common) and continuous length.
That changes the objective compared to classic bin packing: it's not
about using fewer sheets, it's about **unrolling less linear length**. The
empty strip left on the side was already paid for along with the rest.

One constraint comes from the material, not the algorithm: **TNT fabric
has a manufacturing direction.** Rotating a piece 90 degrees changes how it
stretches and resists, so a gown piece that needs to stretch along the
body's direction cannot be rotated, while an internal packaging piece can.
This lives in `Peca.pode_girar`, and the validator rejects any layout that
rotates what shouldn't be rotated.

---

## The validator comes before the heuristics

In nesting, an overlap bug **improves** the metric. If two pieces occupy
the same area of the roll, the computed yield goes up, because the same
surface now counts as two pieces. The number looks good precisely because
it's wrong.

That's why `Layout.validar()` exists before any heuristic, and no result
in this README was reported without passing through it. It checks
pairwise overlap, pieces outside the roll width, negative position, and
forbidden rotation. It's O(n²) and makes no attempt to be fast: it runs
outside the hot path, where correctness matters more than speed.

---

## The heuristics

**Shelf.** Stacks pieces into horizontal shelves. Each shelf takes the
height of the tallest piece placed in it, and new pieces get pushed to the
right until nothing else fits. Simple, and it wastes vertical space: a
shelf opened by a 1200mm piece stays 1200mm tall even if every other piece
in it is 300mm. Two variants: first-fit and best-fit.

**Skyline.** Keeps the real upper contour of what's already been cut,
segment by segment, like a city skyline. A piece can rest on top of two
neighboring low pieces, something shelf packing never sees. Costs more to
maintain and update that profile on every insertion.

---

## Measured results

5 orders per size, generated with a realistic mix of catalog pieces
(small pieces appear far more often than large ones, like a real surgical
kit). 1600mm roll. All layouts validated.

| heuristic | 50 pieces | 200 pieces | 500 pieces | time (500) |
|---|---:|---:|---:|---:|
| Shelf, first-fit | **88.3%** | **90.1%** | **90.3%** | 13.7ms |
| Shelf, best-fit | **88.3%** | **90.1%** | **90.3%** | 13.6ms |
| Skyline | 88.0% | 89.8% | 90.1% | **2.8ms** |
| Skyline, penalize buried | 87.7% | 87.6% | 87.7% | 5.0ms |

### Finding 1: the smarter heuristic doesn't cost more, it's cheaper

Skyline runs **5x faster** than shelf on the 500-piece order (2.8ms vs
13.7ms), despite keeping a more complex data structure. The reason is that
shelf scans the list of open shelves for every piece, and that list keeps
growing (66 shelves in a 200-piece order), while the skyline profile stays
short because neighboring segments at the same height get fused: **3.9
segments on average**, against 66 shelves.

Skyline's cost per piece is roughly constant; shelf's grows with order
size.

### Finding 2: "best-fit" costs time and delivers nothing

Both shelf variants give **identical** yield across all three sizes. That
looked like a bug, and the investigation showed it isn't: they genuinely
diverge (17 out of 200 pieces land in a different position), but the final
length matches **exactly**, across all 5 seeds.

The reason is structural. In the shelf model, total length is the sum of
shelf heights, and a new shelf is only born when **no** existing shelf
fits, a condition identical between both variants. Best-fit only changes
where a piece goes *within* already-open shelves, never how many shelves
exist or how tall they are. It optimizes something that isn't the
bottleneck.

### Finding 3: the "textbook improvement" to skyline made it worse

Bin-packing literature usually breaks ties by minimizing wasted area. In
skyline that would be the area that gets **buried** under a piece: when it
lands on the tallest point of a stretch, the gap over the lower segments
gets sealed off by the profile and nothing else ever occupies it.

I implemented it, measured it across 20 orders, and it got worse:

| tie-break criterion | yield |
|---|---:|
| lowest top, then leftmost | **89.58%** |
| lowest top, then least buried area | 86.67% |
| buried area above everything | 68.28% |

The more weight buried area gets, the worse the result. The cause was
also measured: packing left keeps the skyline as a few wide walls (**3.9
segments** on average, 5.2 at the end), while chasing the least buried
area spreads pieces across the roll and fragments the profile (**5.6
segments**, 9.4 at the end). A fragmented profile has more narrow steps
where nothing else fits. Saving today's gap costs tomorrow's usable
surface.

The default in the code is the criterion that measured better, and the
other stays available as a parameter so the benchmark can show the
difference instead of it becoming a comment.

---

## Run it

```bash
pip install -r requirements.txt
python scripts/comparar_heuristicas.py
```

---

## Current state

| Component | Status |
|---|---|
| Piece, roll and layout model | **Done** |
| Layout validator | **Done** |
| Shelf heuristics (2 variants) | **Done** |
| Skyline heuristic | **Done** |
| Comparative benchmark | **Done** |
| Piece extraction via computer vision | **Done** |
| DXF read/write (CAD) | **Done** |
| Catalog-matching suggestion (AI) | **Done** |
| Cutting plan visualization | **Done** |
| ZPL label export | Planned |
| Web interface | Planned |

---

## Project structure

```
├── src/
│   ├── modelo/
│   │   ├── peca.py           Peca, Rolo, PecaPosicionada and overlap geometry
│   │   ├── layout.py         cutting result, metrics and validator
│   │   └── catalogo.py       disposable hospital-supply pieces, order generation
│   ├── heuristicas/
│   │   ├── faixas.py         shelf: first-fit and best-fit
│   │   └── skyline.py        skyline profile, with both tie-break criteria
│   ├── visao/
│   │   ├── prancha.py        generates a synthetic technical drawing with known ground truth
│   │   └── extrator.py       finds pieces in a drawing via classic OpenCV
│   ├── cad/
│   │   └── dxf.py            reads/writes DXF (real CAD format, via ezdxf)
│   └── ia/
│       ├── sugestor.py       piece autocomplete, from one edge or from a full closing
│       └── historico.py      history of drawn pieces, persisted to disk
├── scripts/
│   ├── comparar_heuristicas.py   measured benchmark, with validation
│   ├── avaliar_extrator.py       recall/precision/error of the vision extractor
│   ├── otimizar.py               CLI: pieces DXF -> cutting plan DXF
│   ├── ver_plano.py              renders a plan DXF as PNG
│   └── sugerir_rascunho.py       CLI: sketch image -> suggested pieces
└── docs/
```

### AI-assisted drawing autocomplete

The original request was "AI integration with CAD, with drawing
assistance, learning from the user." `src/ia/sugestor.py` is the first
version of that, the most honest one that can be validated without a real
technical-drawing dataset: instead of just recognizing a catalog product,
it tries to predict the rest of a piece **before it's finished**.

- `sugerir_por_uma_aresta()` is the real autocomplete: the user has only
  drawn one edge, the piece doesn't exist yet, and the function returns a
  ranked list of how it's likely to end up.
- `sugerir_fechamento()` covers the case where both dimensions are already
  drawn (or extracted from a sketch/photo via `src/visao/extrator.py`) and
  the raw measurement needs to become an exact one.

What makes this learn from the user, not just recognize a fixed product
list, is `src/ia/historico.py`: every piece drawn and confirmed gets
recorded in a history persisted to disk, which both searches above check
**before** the factory catalog (`src/modelo/catalogo.py`) and wins on a
tie. A measurement the user draws every week but that isn't a catalog
product becomes recognized starting the second time.

In both cases, it respects `pode_girar`: a piece whose manufacturing
direction matters is never suggested in an orientation it can't actually
take, even if the raw measurement matches it rotated.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
```

---

## Credits

**Course:** Cyber-Physical Systems Engineering, PUC-SP

Domain grounded in professional experience: 6 months at Systra (technical
drawing in AutoCAD) and work with TNT fabric cutting at Descartee, a
disposable hospital-supply manufacturer.

Catalog piece measurements are plausible order-of-magnitude values for the
industry, not specific product data from any company.
