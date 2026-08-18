# Autocomplete CAD dentro do FreeCAD

Aba nova ("Autocomplete CAD") na lista de workbench do FreeCAD, com um
botão de toolbar: seleciona uma aresta no desenho, clica, escolhe uma das
sugestões, e o retângulo completo é desenhado como objeto novo.

## Como instalar

FreeCAD carrega workbench de tudo que está dentro da pasta `Mod/` da sua
instalação. O addon precisa enxergar o resto do projeto (`src/ia/`), então
o jeito mais simples é linkar o repositório **inteiro**, não só esta
pasta.

**Achar a pasta `Mod/` do FreeCAD:**

- Windows: `%APPDATA%\FreeCAD\Mod\` (normalmente
  `C:\Users\<seu-usuário>\AppData\Roaming\FreeCAD\Mod\`)
- Linux: `~/.local/share/FreeCAD/Mod/`
- macOS: `~/Library/Application Support/FreeCAD/Mod/`

Se a pasta `Mod` não existir ainda, cria ela.

**Windows (PowerShell), link simbólico do repo inteiro:**

```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\FreeCAD\Mod\autocomplete-desenho-cad" -Target "C:\caminho\pra\onde\voce\clonou\autocomplete-desenho-cad"
```

(pode precisar rodar o PowerShell como administrador pra criar symlink)

**Linux/macOS:**

```bash
ln -s /caminho/pra/onde/voce/clonou/autocomplete-desenho-cad ~/.local/share/FreeCAD/Mod/autocomplete-desenho-cad
```

Se preferir não usar link simbólico, também funciona **copiar** o
repositório inteiro pra dentro de `Mod/` (só que aí, quando o projeto
atualizar, precisa copiar de novo).

**Importante:** FreeCAD precisa achar `InitGui.py` na raiz da pasta que
está dentro de `Mod/`. Como o link/cópia aponta pro repositório inteiro
(não só `freecad_addon/`), o FreeCAD só vai reconhecer o workbench se
`InitGui.py` estiver na raiz esperada. Se o seu FreeCAD não achar o
workbench, confirme o caminho `Mod/autocomplete-desenho-cad/freecad_addon/InitGui.py`
existe e, se necessário, linke `freecad_addon/` direto como a pasta do
addon em vez do repositório inteiro. Nesse caso, edite `comandos.py` pra
apontar `_RAIZ_PROJETO` pro caminho absoluto do repositório, já que o
truque de "subir um nível" só funciona linkando o repo inteiro.

## Como usar

1. Abre o FreeCAD, reinicia se ele já estava aberto.
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
  importáveis, o que exige Python 3.10+ no ambiente do FreeCAD (o
  FreeCAD embute o próprio Python; a maioria das versões recentes já
  atende isso, mas se seu FreeCAD for muito antigo pode não funcionar).
