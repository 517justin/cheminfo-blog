"""產生《用 RDKit 玩化學》各集的備用圖（images/fallback.png）與 notebook（epNN.ipynb）。

用法（需要 rdkit==2026.9.1）：
    python make_assets.py            # 全部重做
    python make_assets.py 01 04      # 只做指定集數

notebook 不含執行結果，第一格安裝和書相同版本的 RDKit。
"""

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Draw

POSTS = Path(__file__).resolve().parent.parent / "posts"
INSTALL = "!pip install -q rdkit==2026.9.1"


def fallback_plain(smiles, add_hs=False, size=(400, 300)):
    mol = Chem.MolFromSmiles(smiles)
    if add_hs:
        mol = Chem.AddHs(mol)
    return Draw.MolToImage(mol, size=size)


def fallback_highlight(smiles, smarts, size=(400, 300)):
    mol = Chem.MolFromSmiles(smiles)
    hits = mol.GetSubstructMatches(Chem.MolFromSmarts(smarts))
    atoms = sorted({a for h in hits for a in h})
    bonds = sorted(
        {b.GetIdx() for b in mol.GetBonds()
         if b.GetBeginAtomIdx() in atoms and b.GetEndAtomIdx() in atoms}
    )
    return Draw.MolToImage(mol, size=size, highlightAtoms=atoms, highlightBonds=bonds)


CAFFEINE = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

EPISODES = {
    "01": {
        "dir": "2026-11-rdkit-01-molfromsmiles",
        "title": "電腦怎麼讀懂二氧化碳？",
        "fallback": lambda: fallback_plain("O=C=O"),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("O=C=O")\nmol',
            '# 換你試：換成酒精\nChem.MolFromSmiles("CCO")',
        ],
    },
    "02": {
        "dir": "2026-11-rdkit-02-moltosmiles",
        "title": "同一個分子，為什麼有好幾種寫法？",
        "fallback": lambda: fallback_plain("CCO"),
        "code": [
            'from rdkit import Chem\n\nfor smi in ["CCO", "OCC", "C(O)C"]:\n'
            '    mol = Chem.MolFromSmiles(smi)\n    print(smi, "→", Chem.MolToSmiles(mol))',
            '# 換你試：醋酸的兩種寫法\nfor smi in ["CC(=O)O", "OC(C)=O"]:\n'
            '    print(smi, "→", Chem.MolToSmiles(Chem.MolFromSmiles(smi)))',
        ],
    },
    "04": {
        "dir": "2026-11-rdkit-04-addhs",
        "title": "氫原子躲到哪裡去了？",
        "fallback": lambda: fallback_plain("CCO", add_hs=True),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("CCO")\nmol_h = Chem.AddHs(mol)\n'
            'print(Chem.MolToSmiles(mol_h))\nprint(Chem.MolToSmiles(Chem.RemoveHs(mol_h)))',
            '# 把氫畫出來\nmol_h',
        ],
    },
    "13": {
        "dir": "2026-11-rdkit-13-moltoimage",
        "title": "電腦會畫結構式嗎？",
        "fallback": lambda: fallback_plain(CAFFEINE),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Draw\n\n'
            f'mol = Chem.MolFromSmiles("{CAFFEINE}")\n'
            'Draw.MolToFile(mol, "caffeine.png")\nDraw.MolToImage(mol)',
            '# 換你試：把圖放大\nDraw.MolToImage(mol, size=(600, 400))',
        ],
    },
    "17": {
        "dir": "2026-11-rdkit-17-hassubstructmatch",
        "title": "這個分子有沒有 OH？",
        "fallback": lambda: fallback_highlight("CCO", "[OX2H]"),
        "code": [
            'from rdkit import Chem\n\noh = Chem.MolFromSmarts("[OX2H]")   # 代表 OH 的搜尋條件\n'
            f'for smi in ["CCO", "{CAFFEINE}"]:\n'
            '    print(smi, Chem.MolFromSmiles(smi).HasSubstructMatch(oh))',
            '# 換你試：甲醇\nChem.MolFromSmiles("CO").HasSubstructMatch(oh)',
        ],
    },
}


def notebook(ep, info):
    counter = iter(range(100))

    def cell(kind, text):
        c = {"cell_type": kind, "id": f"cell-{next(counter)}", "metadata": {},
             "source": text.splitlines(keepends=True)}
        if kind == "code":
            c.update(execution_count=None, outputs=[])
        return c

    cells = [
        cell("markdown", f"# 《用 RDKit 玩化學》第 {int(ep)} 集：{info['title']}\n\n"
                         "從上到下依序執行每一格。第一格會安裝 RDKit，大約需要一分鐘。"),
        cell("code", INSTALL),
    ] + [cell("code", c) for c in info["code"]]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main(selected):
    for ep, info in EPISODES.items():
        if selected and ep not in selected:
            continue
        d = POSTS / info["dir"]
        (d / "images").mkdir(parents=True, exist_ok=True)
        info["fallback"]().save(d / "images" / "fallback.png")
        nb = notebook(ep, info)
        (d / f"ep{ep}.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("done", ep, d.name)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
