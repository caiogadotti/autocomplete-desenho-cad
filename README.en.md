<div align="center">

# CAD Drawing Autocomplete

A drawing-assistance tool for CAD. You draw one side of a piece and it
suggests how the piece is likely to finish, comparing against what you've
drawn before or against a reference catalog. Reads and writes real DXF, so
you can open the result in any CAD software.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)

`In progress`

[Português](README.md) &nbsp;·&nbsp; **English**

</div>

---

## Why this project

At Systra I spent 6 months drawing in AutoCAD. A lot of that time wasn't
designing anything new, it was redrawing a piece similar to one I'd
already made, just adjusting the measurement. That kept bugging me: the
CAD software knows what I drew before, why doesn't it suggest the rest on
its own?

There's no ready-made technical-drawing dataset to train a neural network
on this, so I built it without one. `src/ia/` keeps a history of what's
been drawn and compares a new stroke against it (and against a catalog, if
the history is still empty). If it matches within a tolerance, it
suggests closing the piece at that measurement.

---

## The problem, formulated

> Input: a partial technical drawing (a known measurement, or a closed
> rectangle already extracted from a sketch/photo) and what's already
> known about the domain (history of drawn pieces, reference catalog).
> Output: the piece's most likely full measurement, ranked by confidence,
> respecting that domain's geometric constraints.

Technical drawing doesn't have a public annotated dataset the way
handwritten digits or object images do, so training a neural network on
it from scratch isn't realistic for a course project. The problem
formulated above doesn't need that: it's nearest-match search over a
small space (history + catalog), not classification.

---

## How the autocomplete works

`src/ia/sugestor.py` has two functions, for the two moments where there's
something to suggest:

- `sugerir_por_uma_aresta()`: only one edge is drawn, the piece doesn't
  exist yet. Returns a ranked list of how it's likely to end up. This is
  the real autocomplete, suggesting before the drawing is done.
- `sugerir_fechamento()`: both dimensions are already drawn (or came from
  a sketch/photo via `src/visao/extrator.py`), and the function just
  snaps the raw measurement to the closest known one.

`src/ia/historico.py` keeps every piece the user draws and confirms. That
history gets checked before the fixed catalog (`src/modelo/catalogo.py`)
in both functions above, so it wins on a tie. That's what makes a
measurement you draw every week, even one that isn't a catalog product,
get recognized starting the second time.

Both respect `pode_girar`: if the domain has an orientation constraint (in
the example below, the material's manufacturing direction), the piece
never gets suggested rotated even if the measurement would match that way.

Three ways to feed the autocomplete:

- **Partial stroke**: pass the drawn edge's measurement straight into
  `sugerir_por_uma_aresta()`.
- **Real DXF**: `src/cad/dxf.py` reads/writes DXF via `ezdxf`, tested
  round-tripping through FreeCAD.
- **Sketch or photo**: `src/visao/extrator.py` finds rectangles in a
  hand drawing or photo via classic OpenCV (no neural network), discarding
  what isn't a piece (title block, dimension line, sheet outline).
  Validated at 100% recall/precision on synthetic drawings, sub-pixel
  measurement error.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
```

---

## Domain used to validate it: cutting nesting

Drawing autocomplete is easy to make "look like it works" and hard to
measure. To get real numbers instead of just the promise that it should
work, I needed a real problem with a clear metric. I used cutting nesting:
fit rectangular pieces onto a roll of raw material while wasting as little
as possible. That's the cutting stock problem, NP-hard, it has literature
behind it, and yield/heuristics are measurable. I chose this domain
because I see TNT fabric cutting at Descartee and know the problem
firsthand, but the autocomplete itself (`src/ia/`) doesn't know or need to
know the piece is fabric, it just deals with rectangles and measurements.

> Input: a production order (list of rectangular pieces, each with a size
> and whether it can be rotated) and the width of the raw material roll.
> Output: the position of each piece on the roll, minimizing the roll
> length consumed.

The roll has a fixed width and continuous length, which changes the
objective compared to classic bin packing: it's not about using fewer
sheets, it's about **unrolling less linear length**. `Peca.pode_girar`
models the orientation constraint that motivated that field in the
autocomplete: roll material often has a manufacturing direction (fabric
grain, sheet metal grain, leather grain), and rotating 90 degrees changes
how the piece stretches or resists.

### The validator comes before the heuristics

In nesting, an overlap bug **improves** the metric. If two pieces occupy
the same area of the roll, the computed yield goes up, because the same
surface now counts as two pieces. The number looks good precisely because
it's wrong.

That's why `Layout.validar()` exists before any heuristic, and no result
below was reported without passing through it. It checks pairwise overlap,
pieces outside the roll width, negative position, and forbidden rotation.
It's O(n²) and makes no attempt to be fast: it runs outside the hot path,
where correctness matters more than speed.

### The heuristics

**Shelf.** Stacks pieces into horizontal shelves. Each shelf takes the
height of the tallest piece placed in it, and new pieces get pushed to the
right until nothing else fits. Simple, and it wastes vertical space: a
shelf opened by a 1200mm piece stays 1200mm tall even if every other piece
in it is 300mm. Two variants: first-fit and best-fit.

**Skyline.** Keeps the real upper contour of what's already been cut,
segment by segment, like a city skyline. A piece can rest on top of two
neighboring low pieces, something shelf packing never sees. Costs more to
maintain and update that profile on every insertion.

### Measured results

5 orders per size, generated with a realistic mix of catalog pieces
(small pieces appear far more often than large ones, like a real surgical
kit). 1600mm roll. All layouts validated.

| heuristic | 50 pieces | 200 pieces | 500 pieces | time (500) |
|---|---:|---:|---:|---:|
| Shelf, first-fit | **88.3%** | **90.1%** | **90.3%** | 13.7ms |
| Shelf, best-fit | **88.3%** | **90.1%** | **90.3%** | 13.6ms |
| Skyline | 88.0% | 89.8% | 90.1% | **2.8ms** |
| Skyline, penalize buried | 87.7% | 87.6% | 87.7% | 5.0ms |

**Finding 1: the smarter heuristic doesn't cost more, it's cheaper.**
Skyline runs 5x faster than shelf on the 500-piece order (2.8ms vs
13.7ms), despite keeping a more complex data structure. Shelf scans the
list of open shelves for every piece, and that list keeps growing (66
shelves in a 200-piece order), while the skyline profile stays short
because neighboring segments at the same height get fused: 3.9 segments
on average, against 66 shelves.

**Finding 2: "best-fit" costs time and delivers nothing.** Both shelf
variants give identical yield across all three sizes. That looked like a
bug; the investigation showed it isn't. They genuinely diverge (17 out of
200 pieces land in a different position), but the final length matches
exactly, because length equals the sum of shelf heights, and the decision
to open a new shelf is identical between both variants. Best-fit only
changes where a piece goes within already-open shelves, never how many
shelves exist. It optimizes something that isn't the bottleneck.

**Finding 3: the "textbook improvement" to skyline made it worse.**
Bin-packing literature usually breaks ties by minimizing the buried area
(the gap that gets sealed under a piece when it lands on the tallest point
of a stretch). I implemented it, measured it across 20 orders, and it got
worse:

| tie-break criterion | yield |
|---|---:|
| lowest top, then leftmost | **89.58%** |
| lowest top, then least buried area | 86.67% |
| buried area above everything | 68.28% |

Packing left keeps the skyline as a few wide walls (3.9 segments on
average); chasing the least buried area spreads pieces across the roll and
fragments the profile (5.6 segments). A fragmented profile has more narrow
steps where nothing else fits. The default in the code is the criterion
that measured better; the other stays available as a parameter.

```bash
pip install -r requirements.txt
python scripts/comparar_heuristicas.py
```

---

## Current state

| Component | Status |
|---|---|
| Autocomplete by one edge and by closing | **Done** |
| History of drawn pieces | **Done** |
| DXF read/write (CAD) | **Done** |
| Piece extraction via computer vision | **Done** |
| Piece, roll and layout model (test domain) | **Done** |
| Layout validator | **Done** |
| Nesting heuristics (2 shelf variants, skyline) | **Done** |
| Comparative benchmark | **Done** |
| Real-time drawing interface (inside a CAD tool) | Planned |
| ZPL label export | Planned |

---

## Project structure

```
├── src/
│   ├── ia/
│   │   ├── sugestor.py       piece autocomplete, from one edge or from a full closing
│   │   └── historico.py      history of drawn pieces, persisted to disk
│   ├── cad/
│   │   └── dxf.py            reads/writes DXF (real CAD format, via ezdxf)
│   ├── visao/
│   │   ├── prancha.py        generates a synthetic technical drawing with known ground truth
│   │   └── extrator.py       finds pieces in a drawing via classic OpenCV
│   ├── modelo/                 (test domain: cutting nesting)
│   │   ├── peca.py           Peca, Rolo, PecaPosicionada and overlap geometry
│   │   ├── layout.py         cutting result, metrics and validator
│   │   └── catalogo.py       example pieces, order generation
│   └── heuristicas/             (test domain: cutting nesting)
│       ├── faixas.py         shelf: first-fit and best-fit
│       └── skyline.py        skyline profile, with both tie-break criteria
├── scripts/
│   ├── sugerir_rascunho.py       CLI: sketch image -> suggested pieces
│   ├── otimizar.py               CLI: pieces DXF -> cutting plan DXF
│   ├── ver_plano.py              renders a plan DXF as PNG
│   ├── comparar_heuristicas.py   measured benchmark, with validation
│   └── avaliar_extrator.py       recall/precision/error of the vision extractor
└── docs/
```

---

## Credits

**Course:** Cyber-Physical Systems Engineering, PUC-SP

The idea came from 6 months drawing in AutoCAD at Systra. The domain used
to test it (roll-cutting nesting) is based on the TNT fabric cutting I see
at Descartee, but that's just the test scenario, the tool doesn't know or
need to know fabric exists.

Example catalog measurements are just plausible order-of-magnitude values
for the industry, not product data from any specific company.
