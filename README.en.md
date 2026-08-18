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

## How it works

You draw (or already have) an incomplete rectangular piece, and the
system suggests how it finishes. Two situations:

- **Only one side is drawn** (the piece doesn't exist yet): you give it
  that length, the system returns a ranked list of suggestions for how
  the piece is likely to finish. This is the real autocomplete, before
  the drawing is done.
- **Both dimensions already exist** (drawn, or extracted from a sketch
  photo): the system snaps the raw measurement to the closest one it
  already knows.

The suggestion comes from two sources, in this order: your own
**history** of what you've drawn (grows on its own, every confirmed
piece becomes a future example), and a reference **catalog** that serves
as a base before the history has anything in it. None of this is a
neural network: it's nearest-match search, so it works without a
training dataset and without a GPU.

## How to install

```bash
git clone https://github.com/caiogadotti/autocomplete-desenho-cad
cd autocomplete-desenho-cad
pip install -r requirements.txt
```

That's enough to use it from the command line (sketch/photo → the
`sugerir_rascunho.py` CLI, see "How the autocomplete works" below).

**To use it inside FreeCAD** (a new tab with a button, suggestions right
on screen): full step-by-step, with exact paths per operating system, in
[`INSTALL_FREECAD.md`](INSTALL_FREECAD.md). Short version: copy or link
the cloned folder into FreeCAD's `Mod/` folder and restart.

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

Four ways to feed the autocomplete:

- **Partial stroke**: pass the drawn edge's measurement straight into
  `sugerir_por_uma_aresta()`.
- **Inside the CAD tool**: `InitGui.py`/`comandos.py` (repo root) are a
  real FreeCAD workbench, tested inside FreeCAD 1.1.3: a new tab with a
  toolbar button. Select the edge on screen, click, pick a suggestion,
  the rectangle gets drawn. Install steps and v1 limitations in
  [`INSTALL_FREECAD.md`](INSTALL_FREECAD.md).
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
measure. To get real numbers, I used a real problem with a clear metric:
fitting rectangular pieces onto a roll while wasting as little material as
possible, the cutting stock problem, NP-hard. I chose this domain because
I see TNT fabric cutting at Descartee, but the autocomplete (`src/ia/`)
doesn't know or need to know the piece is fabric, it just deals with
rectangles and measurements.

`Layout.validar()` runs before any heuristic and rejects overlap, pieces
outside the roll width, and forbidden rotation, because an overlap bug
improves the yield metric instead of worsening it, which would let a bug
pass as a good result. Two heuristic families compared: shelf (stacks
into horizontal rows) and skyline (keeps the real contour of what's been
cut). The strongest finding: minimizing the buried area under each piece,
the standard bin-packing tie-break, measured **worse** (89.6% → as low as
68.3% depending on how aggressively applied), because it fragments the
profile instead of keeping a few wide segments. Details and the other
comparisons are in the comments of `src/heuristicas/skyline.py` and in
the benchmark.

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
| Test domain (cutting nesting), to validate with real numbers | **Done** |
| Workbench inside FreeCAD (tab + toolbar button) | **Done** (v1) |
| Align suggestion with original edge's position/rotation | Planned |
| Generalize the autocomplete beyond exact nearest-match search | Planned |

---

## Project structure

```
├── InitGui.py                     registers the workbench with FreeCAD (must be at root)
├── comandos.py                    "suggest piece from selected edge" command
├── INSTALL_FREECAD.md             install and usage steps inside FreeCAD
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
