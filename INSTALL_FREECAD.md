# Autocomplete CAD dentro do FreeCAD

Aba nova ("Autocomplete CAD") na lista de workbench do FreeCAD, com um
botão de toolbar: seleciona uma aresta no desenho, clica, escolhe uma das
sugestões, e o retângulo completo é desenhado como objeto novo.

Testado de verdade dentro do FreeCAD 1.1.3 (Windows), não só no papel.

## Como instalar

FreeCAD carrega workbench de tudo que está dentro da pasta `Mod/` da sua
instalação, e só reconhece um addon se `InitGui.py` estiver **direto na
raiz** da pasta (não numa subpasta). É por isso que `InitGui.py` e
`comandos.py` ficam na raiz deste repositório, não numa pasta separada
tipo `freecad_addon/`.

**Achar a pasta `Mod/` certa pra sua versão do FreeCAD:** o caminho muda
de versão pra versão (FreeCAD 1.1 usa uma pasta versionada, por exemplo).
O jeito confiável de achar é perguntar pro próprio FreeCAD: abre o
**Console Python** (menu Ver → Painéis → Python Console) e roda:

```python
print(App.getUserAppDataDir() + "Mod")
```

Isso imprime o caminho exato onde o `Mod/` dessa instalação fica. Em
Windows normalmente é algo como
`C:\Users\<usuário>\AppData\Roaming\FreeCAD\v1-1\Mod` (o `v1-1` muda
conforme a versão instalada). Se a pasta `Mod` ainda não existir, cria ela.

**Link simbólico do repositório inteiro** (recomendado, mantém
atualizado sozinho):

```powershell
# Windows, precisa rodar o PowerShell como administrador
New-Item -ItemType SymbolicLink -Path "<caminho-do-Mod-que-o-FreeCAD-te-deu>\autocomplete-desenho-cad" -Target "C:\caminho\pra\onde\voce\clonou\autocomplete-desenho-cad"
```

```bash
# Linux/macOS
ln -s /caminho/pra/onde/voce/clonou/autocomplete-desenho-cad ~/.local/share/FreeCAD/Mod/autocomplete-desenho-cad
```

**Sem permissão de administrador**, copiar funciona igual, só que
atualização do projeto exige copiar de novo:

```powershell
robocopy "C:\caminho\pro\repo\clonado" "<caminho-do-Mod>\autocomplete-desenho-cad" /E /XD .git __pycache__
```

Reinicia o FreeCAD depois de instalar (ele só escaneia `Mod/` na
abertura).

## Como usar

1. Abre o FreeCAD (ou reinicia se já estava aberto antes de instalar).
2. No seletor de workbench (canto superior esquerdo, onde fica "Part",
   "Draft" etc.), escolhe **Autocomplete CAD**.
3. Desenha ou abre um desenho com pelo menos uma aresta.
4. Seleciona a aresta (clica nela na tela 3D).
5. Clica no botão da toolbar "Sugerir peça (aresta selecionada)".
6. Escolhe uma das sugestões na lista. O retângulo completo é desenhado
   na origem do documento como objeto Draft novo.

## Limitações da v1

- O retângulo sugerido é desenhado na origem `(0,0,0)`, não encostado na
  aresta selecionada. Alinhar automaticamente com posição/rotação da
  aresta original é a próxima etapa.
- Só funciona com aresta reta (linha). Arco/curva não tem "comprimento
  de lado" no sentido que o autocomplete espera.
- Precisa que `src/ia/sugestor.py` e `src/ia/historico.py` estejam
  importáveis, o que exige Python 3.10+ no ambiente do FreeCAD (testado
  com o Python 3.11 embutido no FreeCAD 1.1.3).
