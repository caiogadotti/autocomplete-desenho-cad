<div align="center">

# CAD Drawing Autocomplete

A drawing-assistance tool for CAD. You draw one side of a piece and it
suggests how the piece is likely to finish, comparing against what you've
drawn before or against a reference catalog. Reads and writes real DXF, so
you can open the result in any CAD software.

Not built for a specific material. The fabric-roll cutting example in this
README is just the domain I used to check whether the idea holds up with
real numbers, not the point of the project.

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

To know if this actually works instead of just "sounding good in a
README," I needed a real problem to test it on. I used cutting nesting:
fit rectangular pieces onto a fabric roll while wasting as little as
possible. That's the cutting stock problem, NP-hard, it has literature
behind it, and yield/heuristics are measurable. Why that domain: I see TNT
fabric cutting at Descartee, so I know the problem firsthand. But the
autocomplete itself (`src/ia/`) doesn't know or need to know the piece is
fabric, it just deals with rectangles and measurements.

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
`src/ia/sugerir_por_uma_aresta()` and `sugerir_fechamento()` implement
exactly that search.

The geometric constraint mentioned above (`Peca.pode_girar`) exists
because a technical-drawing piece can't always rotate freely: in the
domain used to test this (roll cutting), the material has a manufacturing
direction, and rotating 90 degrees changes how the piece stretches or
resists. Each new domain that uses `src/ia/` defines its own constraints
this way.

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

Domain used to test this, formulated separately because it's a classic
problem with its own name, the cutting stock problem: given an order of
rectangular pieces (size and whether they can rotate) and the width of a
raw material roll, decide each piece's position minimizing the roll
length consumed. Fixed width and continuous length change the objective
compared to classic bin packing: it's not about using fewer sheets, it's
about **unrolling less linear length**.

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

### The autocomplete itself

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
the fabric example, the manufacturing grain direction), the piece never
gets suggested rotated even if the measurement would match that way.

```bash
python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
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
