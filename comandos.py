"""Comando de toolbar: sugere o fechamento de uma peça a partir da aresta selecionada.

Reusa `src/ia/sugestor.py` direto, sem duplicar a lógica de busca: o addon
é só a cola entre "usuário selecionou uma aresta no FreeCAD" e "chamar
`sugerir_por_uma_aresta` com o comprimento dela".

Este arquivo fica na raiz do repositório, não numa subpasta, porque é
assim que o FreeCAD encontra addon dentro de `Mod/`: ele só olha o
`InitGui.py` que está direto na raiz de cada pasta ali dentro, não
procura em subpastas. Ver `INSTALL_FREECAD.md` pra instalação.
"""

import os
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

_RAIZ_PROJETO = os.path.dirname(os.path.abspath(__file__))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from src.ia.historico import registrar_peca
from src.ia.sugestor import sugerir_por_uma_aresta


class ComandoSugerirAresta:
    """Pega a aresta selecionada no documento ativo e sugere o fechamento da peça.

    Fica deliberadamente burro nessa primeira versão: não desenha nada
    sozinho até o usuário escolher uma sugestão na lista, e escreve o
    resultado como um objeto novo, sem tocar no que já existe no
    documento. O retângulo sai desenhado na origem, não sobre a aresta
    original, porque calcular onde encostar com o desenho já existente
    (rotação, offset) é a próxima etapa planejada, não essa.
    """

    def GetResources(self):
        return {
            "MenuText": "Sugerir peça (aresta selecionada)",
            "ToolTip": "Sugere o fechamento de uma peça a partir da aresta selecionada",
        }

    def IsActive(self):
        return App.ActiveDocument is not None and len(Gui.Selection.getSelection()) > 0

    def Activated(self):
        selecao = Gui.Selection.getSelectionEx()
        if not selecao:
            QtGui.QMessageBox.warning(None, "Autocomplete CAD", "Selecione uma aresta antes de rodar o comando.")
            return

        # Clicar na aresta na tela 3D preenche `SubObjects` com o Edge
        # exato. Selecionar o objeto inteiro pela árvore não preenche
        # `SubObjects` (é assim que o FreeCAD trata seleção sem
        # sub-elemento), então cai aqui: se o objeto só tem uma aresta,
        # usa ela, sem forçar o usuário a saber dessa diferença.
        if selecao[0].SubObjects:
            aresta = selecao[0].SubObjects[0]
        else:
            forma = getattr(selecao[0].Object, "Shape", None)
            if forma is None or len(forma.Edges) != 1:
                QtGui.QMessageBox.warning(
                    None, "Autocomplete CAD",
                    "Selecione uma aresta específica (clique nela na tela 3D), "
                    "não o objeto inteiro, já que ele tem mais de uma aresta.",
                )
                return
            aresta = forma.Edges[0]

        if not hasattr(aresta, "Length"):
            QtGui.QMessageBox.warning(None, "Autocomplete CAD", "O objeto selecionado não é uma aresta.")
            return

        comprimento_mm = aresta.Length
        sugestoes = sugerir_por_uma_aresta(comprimento_mm)

        if not sugestoes:
            QtGui.QMessageBox.information(
                None,
                "Autocomplete CAD",
                f"Nenhuma sugestão pra uma aresta de {comprimento_mm:.1f}mm "
                "(nada no histórico/catálogo dentro da tolerância).",
            )
            return

        opcoes = [
            f"{s.largura_mm} x {s.altura_mm} mm   {s.nome or 'sem nome'}   [{s.origem}, {s.confianca:.0%}]"
            for s in sugestoes
        ]
        escolha, confirmado = QtGui.QInputDialog.getItem(
            None, "Autocomplete CAD", "Sugestões pra essa aresta:", opcoes, 0, False,
        )
        if not confirmado:
            return

        sugestao = sugestoes[opcoes.index(escolha)]
        self._desenhar_retangulo(sugestao)

    def _desenhar_retangulo(self, sugestao):
        import Draft

        p1 = App.Vector(0, 0, 0)
        p2 = App.Vector(sugestao.largura_mm, 0, 0)
        p3 = App.Vector(sugestao.largura_mm, sugestao.altura_mm, 0)
        p4 = App.Vector(0, sugestao.altura_mm, 0)

        retangulo = Draft.make_wire([p1, p2, p3, p4], closed=True)
        retangulo.Label = sugestao.nome or "peca-sugerida"
        App.ActiveDocument.recompute()

        if sugestao.nome:
            registrar_peca(sugestao.nome, sugestao.largura_mm, sugestao.altura_mm, pode_girar=True)
