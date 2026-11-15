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


def fallback_highlight_indices(smiles, smarts, size=(400, 300)):
    mol = Chem.MolFromSmiles(smiles)
    atoms = sorted({a for h in mol.GetSubstructMatches(Chem.MolFromSmarts(smarts)) for a in h})
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    d.drawOptions().addAtomIndices = True
    d.DrawMolecule(mol, highlightAtoms=atoms)
    d.FinishDrawing()
    from io import BytesIO
    from PIL import Image
    return Image.open(BytesIO(d.GetDrawingText()))


def fallback_filter(named, smarts):
    q = Chem.MolFromSmarts(smarts)
    mols = [Chem.MolFromSmiles(s) for _, s in named]
    legends = [f"{n}: {'yes' if m.HasSubstructMatch(q) else 'no'}" for (n, _), m in zip(named, mols)]
    return Draw.MolsToGridImage(mols, molsPerRow=3, subImgSize=(220, 160), legends=legends)


def _png(drawer):
    from io import BytesIO
    from PIL import Image
    drawer.FinishDrawing()
    return Image.open(BytesIO(drawer.GetDrawingText()))


def fallback_indices(smiles, size=(400, 300)):
    mol = Chem.MolFromSmiles(smiles)
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    d.drawOptions().addAtomIndices = True
    d.DrawMolecule(mol)
    return _png(d)


BOND_COLORS = {"SINGLE": (0.55, 0.75, 1.0), "DOUBLE": (1.0, 0.65, 0.3),
               "TRIPLE": (0.8, 0.5, 1.0), "AROMATIC": (0.4, 0.8, 0.4)}


def fallback_bonds(smiles, size=(400, 300)):
    """鍵依種類塗色，顏色和網頁小框相同。"""
    mol = Chem.MolFromSmiles(smiles)
    colors = {b.GetIdx(): BOND_COLORS[str(b.GetBondType())] for b in mol.GetBonds()}
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    Draw.rdMolDraw2D.PrepareAndDrawMolecule(d, mol, highlightAtoms=[], highlightBonds=list(colors),
                                            highlightBondColors=colors, kekulize=False)
    return _png(d)


def fallback_kekule(smiles, size=(300, 240)):
    """左邊芳香寫法（虛線是芳香鍵），右邊單雙鍵交替寫法。"""
    from PIL import Image
    mol = Chem.MolFromSmiles(smiles)
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    Draw.rdMolDraw2D.PrepareAndDrawMolecule(d, mol, kekulize=False)
    left = _png(d)
    kek = Chem.Mol(mol)
    Chem.Kekulize(kek, clearAromaticFlags=True)
    right = Draw.MolToImage(kek, size=size)
    out = Image.new("RGB", (size[0] * 2, size[1]), "white")
    out.paste(left.convert("RGB"), (0, 0))
    out.paste(right.convert("RGB"), (size[0], 0))
    return out


def fallback_grid(named, size=(260, 200)):
    mols = [Chem.MolFromSmiles(s) for _, s in named]
    return Draw.MolsToGridImage(mols, molsPerRow=len(mols), subImgSize=size, legends=[n for n, _ in named])


def fallback_neighbors(smiles, idx, size=(400, 300)):
    """選到的原子塗藍綠色、鄰居塗橘色，顏色和網頁小框相同。"""
    mol = Chem.MolFromSmiles(smiles)
    atom = mol.GetAtomWithIdx(idx)
    near = [n.GetIdx() for n in atom.GetNeighbors()]
    colors = {idx: (0.3, 0.75, 0.82), **{j: (1.0, 0.7, 0.35) for j in near}}
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    d.drawOptions().addAtomIndices = True
    d.DrawMolecule(mol, highlightAtoms=[idx] + near, highlightAtomColors=colors, highlightBonds=[])  # 鍵不上色
    return _png(d)


def fallback_two(left, right, size=(300, 220), indices=False, hl_left=()):
    """兩張結構圖並排；indices=True 時標出原子編號。"""
    from PIL import Image
    ims = []
    for smi, hl in ((left, hl_left), (right, ())):
        d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
        d.drawOptions().addAtomIndices = indices
        d.DrawMolecule(Chem.MolFromSmiles(smi), highlightAtoms=list(hl), highlightBonds=[])
        ims.append(_png(d).convert("RGB"))
    out = Image.new("RGB", (size[0] * 2, size[1]), "white")
    out.paste(ims[0], (0, 0))
    out.paste(ims[1], (size[0], 0))
    return out


def fallback_pick(smiles, atoms, size=(400, 300)):
    d = Draw.rdMolDraw2D.MolDraw2DCairo(*size)
    d.drawOptions().addAtomIndices = True
    d.DrawMolecule(Chem.MolFromSmiles(smiles), highlightAtoms=list(atoms), highlightBonds=[])
    return _png(d)


THEOBROMINE = "Cn1cnc2c1c(=O)[nH]c(=O)n2C"


def fallback_legend_grid(named, per_row=None, size=(240, 190)):
    mols = [Chem.MolFromSmiles(x) for _, x in named]
    return Draw.MolsToGridImage(mols, molsPerRow=per_row or len(mols), subImgSize=size, legends=[n for n, _ in named])


def fallback_barcode(smiles, bits=64):
    """結構圖下面接一條 64 格的條碼（深色是 1）。"""
    from PIL import Image, ImageDraw
    from rdkit.Chem import rdFingerprintGenerator
    fp = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=bits).GetFingerprint(Chem.MolFromSmiles(smiles))
    top = Draw.MolToImage(Chem.MolFromSmiles(smiles), size=(400, 240)).convert("RGB")
    w, cell = 640, 20
    out = Image.new("RGB", (w, 240 + 2 * cell + 40), "white")
    out.paste(top, ((w - 400) // 2, 0))
    d = ImageDraw.Draw(out)
    for i, b in enumerate(fp.ToBitString()):
        x, y = (i % 32) * cell, 250 + (i // 32) * (cell + 4)
        d.rectangle((x + 1, y, x + cell - 2, y + cell), fill=(33, 37, 41) if b == "1" else (233, 236, 239))
    return out


def fallback_mcs(a, b, size=(300, 220)):
    from PIL import Image
    from rdkit.Chem import rdFMCS
    ma, mb = Chem.MolFromSmiles(a), Chem.MolFromSmiles(b)
    q = Chem.MolFromSmarts(rdFMCS.FindMCS([ma, mb]).smartsString)
    ims = []
    for m in (ma, mb):
        atoms = list(m.GetSubstructMatch(q))
        bonds = [bd.GetIdx() for bd in m.GetBonds() if bd.GetBeginAtomIdx() in atoms and bd.GetEndAtomIdx() in atoms]
        ims.append(Draw.MolToImage(m, size=size, highlightAtoms=atoms, highlightBonds=bonds).convert("RGB"))
    out = Image.new("RGB", (size[0] * 2, size[1]), "white")
    out.paste(ims[0], (0, 0))
    out.paste(ims[1], (size[0], 0))
    return out


def embed_3d(smiles, seed=42):
    """加氫、算 3D 座標（和第 26 集的程式相同），回傳原子、鍵的清單。"""
    from rdkit.Chem import AllChem
    m = Chem.AddHs(Chem.MolFromSmiles(smiles))
    assert AllChem.EmbedMolecule(m, randomSeed=seed) == 0
    c = m.GetConformer()
    atoms = [[a.GetSymbol(), *[round(v, 3) for v in c.GetAtomPosition(a.GetIdx())]] for a in m.GetAtoms()]
    Chem.Kekulize(m, clearAromaticFlags=True)
    bonds = [[b.GetBeginAtomIdx(), b.GetEndAtomIdx(), int(b.GetBondTypeAsDouble())] for b in m.GetBonds()]
    return atoms, bonds


def spin_config():
    """第 26 集小框的設定：事先算好的 3D 座標。"""
    spin_molecules = [("酒精（乙醇）", "CCO"), ("甲烷（天然氣的主要成分）", "C"), ("水", "O"), ("二氧化碳", "O=C=O"),
                      ("咖啡因", CAFFEINE), ("葡萄糖", GLUCOSE)]
    mols = []
    for name, smi in spin_molecules:
        atoms, bonds = embed_3d(smi)
        mols.append({"name": name, "atoms": atoms, "bonds": bonds})
    return json.dumps({"molecules": mols}, ensure_ascii=False, separators=(",", ":"))


def fallback_3d(smiles, size=(420, 320), rot=(-0.4, 0.6)):
    """把 3D 座標畫成有遠近的球棒模型（PIL），和網頁小框的畫法相同。"""
    import math
    from PIL import Image, ImageDraw
    atoms, bonds = embed_3d(smiles)
    colors = {"C": (73, 80, 87), "O": (240, 62, 62), "N": (51, 154, 240), "H": (248, 249, 250)}
    radius = {"H": 0.25, "C": 0.4, "N": 0.4, "O": 0.42}
    n = len(atoms)
    c = [sum(a[k + 1] for a in atoms) / n for k in range(3)]
    pts = [(a[1] - c[0], a[2] - c[1], a[3] - c[2]) for a in atoms]
    r = max(math.hypot(*p) for p in pts) + 0.6
    scale = min(size) * 0.43 / r
    rx, ry = rot
    P = []
    for x, y, z in pts:
        x1, z1 = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y1, z2 = y * math.cos(rx) - z1 * math.sin(rx), y * math.sin(rx) + z1 * math.cos(rx)
        f = 6 / (6 - z2)
        P.append((size[0] / 2 + x1 * scale * f, size[1] / 2 - y1 * scale * f, z2, f))
    im = Image.new("RGB", size, (248, 249, 250))
    d = ImageDraw.Draw(im)
    items = [((P[i][2] + P[j][2]) / 2 - 0.01, "b", (i, j)) for i, j, _ in bonds] + [(P[i][2], "a", i) for i in range(n)]
    for _, kind, v in sorted(items, key=lambda t: t[0]):
        if kind == "b":
            i, j = v
            d.line((P[i][0], P[i][1], P[j][0], P[j][1]), fill=(173, 181, 189), width=6)
        else:
            sym = atoms[v][0]
            rr = radius.get(sym, 0.45) * scale * P[v][3]
            d.ellipse((P[v][0] - rr, P[v][1] - rr, P[v][0] + rr, P[v][1] + rr), fill=colors.get(sym, (174, 62, 201)),
                      outline=(173, 181, 189) if sym == "H" else None, width=2)
    return im


def fallback_rings(smiles, size=(400, 300)):
    mol = Chem.MolFromSmiles(smiles)
    ri = mol.GetRingInfo()
    atoms = sorted({a for r in ri.AtomRings() for a in r})
    bonds = sorted({b for r in ri.BondRings() for b in r})
    return Draw.MolToImage(mol, size=size, highlightAtoms=atoms, highlightBonds=bonds)


CAFFEINE = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
GLUCOSE = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"
SUCROSE = "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@@H]1O"

EPISODES = {
    "22": {
        "dir": "2026-11-rdkit-22-mollogp",
        "title": "喜歡水還是喜歡油？",
        "fallback": lambda: fallback_legend_grid(
            [("glucose  logP -3.22", GLUCOSE), ("caffeine  -1.03", CAFFEINE), ("ethanol  0.00", "CCO"),
             ("benzene  1.69", "c1ccccc1"), ("hexane  2.59", "CCCCCC")], size=(200, 170)),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Descriptors\n\n'
            f'for smi in ["{GLUCOSE}", "CCO", "CCCCCC"]:\n'
            '    print(f"{Descriptors.MolLogP(Chem.MolFromSmiles(smi)):.2f}")',
            f'# 換你試：咖啡因、己醇\nfor smi in ["{CAFFEINE}", "CCCCCCO"]:\n'
            '    print(f"{Descriptors.MolLogP(Chem.MolFromSmiles(smi)):.2f}")',
        ],
    },
    "23": {
        "dir": "2026-11-rdkit-23-morganfingerprint",
        "title": "分子的條碼",
        "fallback": lambda: fallback_barcode("CCO"),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import rdFingerprintGenerator\n\n'
            'gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=64)\n'
            'fp = gen.GetFingerprint(Chem.MolFromSmiles("CCO"))\nprint(fp.ToBitString())',
            '# 換你試：甲醇的條碼，和酒精哪幾格不一樣\n'
            'print(gen.GetFingerprint(Chem.MolFromSmiles("CO")).ToBitString())',
        ],
    },
    "24": {
        "dir": "2026-11-rdkit-24-tanimotosimilarity",
        "title": "兩個分子有多像？",
        "fallback": lambda: fallback_legend_grid([("ethanol", "CCO"), ("methanol  (similarity 0.286)", "CO")], size=(300, 200)),
        "code": [
            'from rdkit import Chem, DataStructs\nfrom rdkit.Chem import rdFingerprintGenerator\n\n'
            'gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)\n'
            'fp = lambda s: gen.GetFingerprint(Chem.MolFromSmiles(s))\n'
            'print(round(DataStructs.TanimotoSimilarity(fp("CCO"), fp("CO")), 3))',
            f'# 換你試：咖啡因和可可鹼、咖啡因和茶鹼\n'
            f'print(round(DataStructs.TanimotoSimilarity(fp("{CAFFEINE}"), fp("{THEOBROMINE}")), 3))\n'
            f'print(round(DataStructs.TanimotoSimilarity(fp("{CAFFEINE}"), fp("Cn1c(=O)c2[nH]cnc2n(C)c1=O")), 3))',
        ],
    },
    "25": {
        "dir": "2026-11-rdkit-25-findmcs",
        "title": "咖啡因和巧克力裡的可可鹼差在哪？",
        "fallback": lambda: fallback_mcs(CAFFEINE, THEOBROMINE),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import rdFMCS\n\n'
            f'caffeine = Chem.MolFromSmiles("{CAFFEINE}")\ntheobromine = Chem.MolFromSmiles("{THEOBROMINE}")\n'
            'print(rdFMCS.FindMCS([caffeine, theobromine]).numAtoms)',
            '# 換你試：咖啡因和茶鹼\ntheophylline = Chem.MolFromSmiles("Cn1c(=O)c2[nH]cnc2n(C)c1=O")\n'
            'print(rdFMCS.FindMCS([caffeine, theophylline]).numAtoms)',
        ],
    },
    "26": {
        "dir": "2026-11-rdkit-26-embedmolecule",
        "title": "分子其實是立體的",
        "fallback": lambda: fallback_3d("CCO"),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import AllChem\n\n'
            'mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))\nprint(AllChem.EmbedMolecule(mol, randomSeed=42))\n'
            'print(mol.GetConformer().Is3D())',
            '# 換你試：換一個 randomSeed，看看第一個原子的座標\nAllChem.EmbedMolecule(mol, randomSeed=7)\n'
            'print(list(mol.GetConformer().GetAtomPosition(0)))',
        ],
    },
    "14": {
        "dir": "2026-11-rdkit-14-molstogridimage",
        "title": "廚房裡的分子排排站",
        "fallback": lambda: Draw.MolsToGridImage(
            [Chem.MolFromSmiles(x) for x in ["O", "[Na+].[Cl-]", "CC(=O)O", "CCO", "[Na+].OC([O-])=O"]],
            legends=["water", "salt", "vinegar", "alcohol", "baking soda"], molsPerRow=3, subImgSize=(220, 180)),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Draw\n\n'
            'smiles = ["O", "[Na+].[Cl-]", "CC(=O)O", "CCO", "[Na+].OC([O-])=O"]\n'
            'names = ["water", "salt", "vinegar", "alcohol", "baking soda"]\n'
            'Draw.MolsToGridImage([Chem.MolFromSmiles(s) for s in smiles], legends=names, molsPerRow=3)',
            '# 換你試：每排 2 個\nDraw.MolsToGridImage([Chem.MolFromSmiles(s) for s in smiles], legends=names, molsPerRow=2)',
        ],
    },
    "15": {
        "dir": "2026-11-rdkit-15-addatomindices",
        "title": "幫原子編號",
        "fallback": lambda: fallback_two("CCO", "OCC", indices=True),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Draw\n\nopts = Draw.MolDrawOptions()\nopts.addAtomIndices = True\n'
            'Draw.MolToImage(Chem.MolFromSmiles("CCO"), options=opts)',
            '# 換你試：換一種寫法，編號跟著變\nDraw.MolToImage(Chem.MolFromSmiles("OCC"), options=opts)',
        ],
    },
    "16": {
        "dir": "2026-11-rdkit-16-highlightatoms",
        "title": "幫一塊結構塗顏色",
        "fallback": lambda: fallback_pick("CCO", [2]),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Draw\n\nmol = Chem.MolFromSmiles("CCO")\n'
            'Draw.MolToImage(mol, highlightAtoms=[2])   # 2 號原子是氧',
            '# 換你試：把兩個碳塗起來\nDraw.MolToImage(mol, highlightAtoms=[0, 1])',
        ],
    },
    "19": {
        "dir": "2026-11-rdkit-19-deletesubstructs",
        "title": "把酒精的 OH 拿掉會怎樣？",
        "fallback": lambda: fallback_two("CCO", "CC", hl_left=[2]),
        "code": [
            'from rdkit import Chem\n\noh = Chem.MolFromSmarts("[OX2H]")\n'
            'mol = Chem.DeleteSubstructs(Chem.MolFromSmiles("CCO"), oh)\nprint(Chem.MolToSmiles(mol))',
            '# 換你試：苯酚、醋酸、甘油\nfor smi in ["Oc1ccccc1", "CC(=O)O", "OCC(O)CO"]:\n'
            '    print(smi, "->", Chem.MolToSmiles(Chem.DeleteSubstructs(Chem.MolFromSmiles(smi), oh)))',
        ],
    },
    "20": {
        "dir": "2026-11-rdkit-20-reactionfromsmarts",
        "title": "酒為什麼會變醋？",
        "fallback": lambda: fallback_two("CCO", "CC(=O)O", hl_left=[1, 2]),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import AllChem\n\n'
            'rxn = AllChem.ReactionFromSmarts("[CX4;H2,H3:1][OH:2]>>[C:1](=O)[OH:2]")\n'
            'products = rxn.RunReactants((Chem.MolFromSmiles("CCO"),))\nprint(Chem.MolToSmiles(products[0][0]))',
            '# 換你試：甲醇、丙醇、異丙醇\nfor smi in ["CO", "CCCO", "CC(C)O"]:\n'
            '    products = rxn.RunReactants((Chem.MolFromSmiles(smi),))\n'
            '    print(smi, [Chem.MolToSmiles(p[0]) for p in products])',
        ],
    },
    "06": {
        "dir": "2026-11-rdkit-06-molwt",
        "title": "電腦會算分子量嗎？",
        "fallback": lambda: fallback_plain("O"),
        "code": [
            'from rdkit import Chem\nfrom rdkit.Chem import Descriptors, rdMolDescriptors\n\n'
            'mol = Chem.MolFromSmiles("CCO")\nprint(rdMolDescriptors.CalcMolFormula(mol))\nprint(round(Descriptors.MolWt(mol), 2))',
            f'# 換你試：葡萄糖、果糖、蔗糖的分子量\nfor smi in ["{GLUCOSE}", "OCC(=O)[C@@H](O)[C@H](O)[C@H](O)CO", "{SUCROSE}"]:\n'
            '    print(round(Descriptors.MolWt(Chem.MolFromSmiles(smi)), 2))',
        ],
    },
    "07": {
        "dir": "2026-11-rdkit-07-getneighbors",
        "title": "這個原子旁邊接了誰？",
        "fallback": lambda: fallback_neighbors("CCO", 1),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("CCO")\natom = mol.GetAtomWithIdx(1)\n'
            'print(atom.GetSymbol(), atom.GetDegree())\nprint([n.GetIdx() for n in atom.GetNeighbors()])\n'
            'print(atom.GetTotalNumHs())',
            '# 換你試：醋酸的 1 號碳，雙鍵相連的氧只算一個鄰居\nacetic = Chem.MolFromSmiles("CC(=O)O")\n'
            'print([n.GetIdx() for n in acetic.GetAtomWithIdx(1).GetNeighbors()])',
        ],
    },
    "08": {
        "dir": "2026-11-rdkit-08-getatoms",
        "title": "每個原子是什麼元素？",
        "fallback": lambda: fallback_indices("CCO"),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("CCO")\nfor atom in mol.GetAtoms():\n'
            '    print(atom.GetIdx(), atom.GetSymbol())',
            f'# 換你試：咖啡因裡的氮\ncaffeine = Chem.MolFromSmiles("{CAFFEINE}")\n'
            'print([atom.GetIdx() for atom in caffeine.GetAtoms() if atom.GetSymbol() == "N"])',
        ],
    },
    "09": {
        "dir": "2026-11-rdkit-09-getbonds",
        "title": "單鍵、雙鍵、三鍵怎麼分？",
        "fallback": lambda: fallback_bonds("CC(=O)O"),
        "code": [
            'from rdkit import Chem\n\nfor smi in ["CCO", "O=C=O", "C#C"]:\n    mol = Chem.MolFromSmiles(smi)\n'
            '    print(smi, [str(b.GetBondType()) for b in mol.GetBonds()])',
            '# 換你試：苯和丁二烯\nfor smi in ["c1ccccc1", "C=CC=C"]:\n    mol = Chem.MolFromSmiles(smi)\n'
            '    print(smi, [str(b.GetBondType()) for b in mol.GetBonds()])',
        ],
    },
    "11": {
        "dir": "2026-11-rdkit-11-kekulize",
        "title": "苯為什麼有兩種寫法？",
        "fallback": lambda: fallback_kekule("c1ccccc1"),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("c1ccccc1")\n'
            'Chem.Kekulize(mol, clearAromaticFlags=True)\nprint(Chem.MolToSmiles(mol))',
            '# 換你試：兩種寫法讀進來後是不是一樣\n'
            'print(Chem.MolToSmiles(Chem.MolFromSmiles("C1=CC=CC=C1")), Chem.MolToSmiles(Chem.MolFromSmiles("c1ccccc1")))',
        ],
    },
    "12": {
        "dir": "2026-11-rdkit-12-getmolfrags",
        "title": "電腦看得懂食鹽嗎？",
        "fallback": lambda: fallback_grid([("Na+  (+1)", "[Na+]"), ("Cl-  (-1)", "[Cl-]")], size=(200, 160)),
        "code": [
            'from rdkit import Chem\n\nmol = Chem.MolFromSmiles("[Na+].[Cl-]")\nfor atom in mol.GetAtoms():\n'
            '    print(atom.GetSymbol(), atom.GetFormalCharge())\nprint(len(Chem.GetMolFrags(mol)))',
            '# 換你試：小蘇打（碳酸氫鈉）拆成幾塊\nbaking_soda = Chem.MolFromSmiles("[Na+].OC([O-])=O")\n'
            'for frag in Chem.GetMolFrags(baking_soda, asMols=True):\n    print(Chem.MolToSmiles(frag))',
        ],
    },
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
        "fallback": lambda: fallback_filter(
            [("ethanol", "CCO"), ("methanol", "CO"), ("acetic acid", "CC(=O)O"),
             ("glucose", GLUCOSE), ("glycerol", "OCC(O)CO"), ("caffeine", CAFFEINE),
             ("CO2", "O=C=O"), ("benzene", "c1ccccc1"), ("urea", "NC(N)=O")],
            "[OX2H]"),
        "code": [
            'from rdkit import Chem\n\noh = Chem.MolFromSmarts("[OX2H]")   # 代表 OH 的搜尋條件\n'
            f'molecules = {{"酒精": "CCO", "咖啡因": "{CAFFEINE}",\n'
            f'             "葡萄糖": "{GLUCOSE}", "苯": "c1ccccc1"}}\n'
            'for name, smi in molecules.items():\n'
            '    print(name, Chem.MolFromSmiles(smi).HasSubstructMatch(oh))',
            '# 換你試：丙醇\nChem.MolFromSmiles("CCCO").HasSubstructMatch(oh)',
        ],
    },
    "03": {
        "dir": "2026-11-rdkit-03-smiles-errors",
        "title": "打錯字，電腦會發現嗎？",
        "fallback": lambda: fallback_plain("O=C=O"),
        "code": [
            'from rdkit import Chem\n\nfor smi in ["O=C=O", "O=C=", "C(C"]:\n'
            '    print(smi, Chem.MolFromSmiles(smi) is None)',
            '# 換你試：環沒有收尾，以及只接四根鍵的新戊烷\n'
            'for smi in ["C1CC", "C(C)(C)(C)C"]:\n    print(smi, Chem.MolFromSmiles(smi) is None)',
        ],
    },
    "05": {
        "dir": "2026-11-rdkit-05-getnumatoms",
        "title": "分子裡有幾個原子、幾個鍵？",
        "fallback": lambda: fallback_plain(CAFFEINE),
        "code": [
            f'from rdkit import Chem\n\nfor smi in ["CCO", "{CAFFEINE}"]:\n'
            '    mol = Chem.MolFromSmiles(smi)\n    print(mol.GetNumAtoms(), mol.GetNumBonds())',
            '# 換你試：把氫也算進去\nmol_h = Chem.AddHs(Chem.MolFromSmiles("CCO"))\n'
            'print(mol_h.GetNumAtoms(), mol_h.GetNumBonds())',
        ],
    },
    "10": {
        "dir": "2026-11-rdkit-10-getringinfo",
        "title": "分子裡有沒有環？",
        "fallback": lambda: fallback_rings(GLUCOSE),
        "code": [
            f'from rdkit import Chem\n\nfor smi in ["{GLUCOSE}", "{CAFFEINE}"]:\n'
            '    mol = Chem.MolFromSmiles(smi)\n    print(mol.GetRingInfo().NumRings())',
            f'# 換你試：蔗糖（砂糖）有幾個環？\nsucrose = Chem.MolFromSmiles("{SUCROSE}")\nprint(sucrose.GetRingInfo().NumRings())',
        ],
    },
    "18": {
        "dir": "2026-11-rdkit-18-getsubstructmatches",
        "title": "葡萄糖有幾個 OH？",
        "fallback": lambda: fallback_highlight_indices(GLUCOSE, "[OX2H]"),
        "code": [
            'from rdkit import Chem\n\noh = Chem.MolFromSmarts("[OX2H]")\n'
            f'glucose = Chem.MolFromSmiles("{GLUCOSE}")\n'
            'matches = glucose.GetSubstructMatches(oh)\nprint(matches)\nprint(len(matches))',
            f'# 換你試：蔗糖（砂糖）和甘油\nfor smi in ["{SUCROSE}", "OCC(O)CO"]:\n'
            '    print(len(Chem.MolFromSmiles(smi).GetSubstructMatches(oh)))',
        ],
    },
    "21": {
        "dir": "2026-11-rdkit-21-moltoinchikey",
        "title": "分子也有身分證？",
        "fallback": lambda: fallback_plain("CCO"),
        "code": [
            'from rdkit import Chem\n\nfor smi in ["CCO", "OCC"]:\n'
            '    print(Chem.MolToInchiKey(Chem.MolFromSmiles(smi)))',
            '# 換你試：二甲醚的身分證和酒精哪裡不同？\nprint(Chem.MolToInchiKey(Chem.MolFromSmiles("COC")))',
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
        if ep == "26":  # 把 3D 座標寫進文章裡的小框設定
            qmd = d / "index.qmd"
            text = qmd.read_text(encoding="utf-8")
            head, rest = text.split('data-mode="spin">\n<script type="application/json">\n', 1)
            rest = rest.split("\n</script>", 1)[1]
            qmd.write_text(head + 'data-mode="spin">\n<script type="application/json">\n' + spin_config()
                           + "\n</script>" + rest, encoding="utf-8")
        nb = notebook(ep, info)
        (d / f"ep{ep}.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("done", ep, d.name)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
