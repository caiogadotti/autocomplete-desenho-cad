"""Registra o workbench "Autocomplete CAD" no FreeCAD.

FreeCAD descobre workbench por convenção: uma pasta em `Mod/` com um
`InitGui.py` que, ao ser importado, chama `Gui.addWorkbench(...)` com uma
instância de uma classe que herda de `Workbench`. Não tem manifest nem
registro central, é só isso.

O import de `comandos` (que faz o trabalho de verdade) fica dentro de
`Initialize()`, não no topo do arquivo, porque o FreeCAD importa todo
InitGui.py de todo addon instalado logo na abertura, mesmo os workbenches
que o usuário nunca vai abrir. Import pesado aqui no topo deixaria o
FreeCAD inteiro mais lento pra iniciar, não só este addon.
"""

import FreeCADGui as Gui


class AutocompleteCADWorkbench(Gui.Workbench):
    MenuText = "Autocomplete CAD"
    ToolTip = "Sugere o fechamento de uma peça a partir de um traço parcial"
    Icon = ""

    def Initialize(self):
        import comandos

        Gui.addCommand("Autocomplete_SugerirAresta", comandos.ComandoSugerirAresta())
        self.appendToolbar("Autocomplete CAD", ["Autocomplete_SugerirAresta"])
        self.appendMenu("Autocomplete CAD", ["Autocomplete_SugerirAresta"])

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(AutocompleteCADWorkbench())
