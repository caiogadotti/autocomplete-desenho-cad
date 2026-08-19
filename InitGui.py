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
        # `InitGui.py` não roda como import normal (o FreeCAD executa o
        # conteúdo do arquivo sem definir `__file__` nesse namespace, então
        # o truque comum de achar a própria pasta via `__file__` quebra com
        # "name '__file__' is not defined" (erro real, visto testando
        # dentro do FreeCAD de verdade). Não precisa desse truque de
        # qualquer forma: o FreeCAD já adiciona a pasta de cada addon em
        # `Mod/` ao `sys.path` sozinho, então `import comandos` funciona
        # direto, contanto que `comandos.py` esteja ao lado deste arquivo.
        import comandos

        Gui.addCommand("Autocomplete_SugerirAresta", comandos.ComandoSugerirAresta())
        Gui.addCommand("Autocomplete_GerarPeca", comandos.ComandoGerarPeca())
        comandos_addon = ["Autocomplete_SugerirAresta", "Autocomplete_GerarPeca"]
        self.appendToolbar("Autocomplete CAD", comandos_addon)
        self.appendMenu("Autocomplete CAD", comandos_addon)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(AutocompleteCADWorkbench())
