# 電腦也會化學

化學資訊學（Cheminformatics）的繁體中文網站，想讓更多人知道化學也可以交給電腦來處理。

網站：<https://517justin.github.io/cheminfo-blog/>

## 內容

- **《用 RDKit 玩化學》等化學資訊學科普文章**：給所有人的入門系列，一集三分鐘、一集一個 RDKit 功能。每集都有網頁小框可以直接玩分子，另附 Colab notebook。[系列介紹](https://517justin.github.io/cheminfo-blog/rdkit/)
- **化學資訊學的論文實作筆記**：挑選論文，動手重現其中的方法（陸續加入）。
- **化學資訊學的進階技術實作**：進階技術的實作筆記（陸續加入）。

想有系統地學，可以搭配教科書《[化學資訊學入門](https://517justin.github.io/cheminfo-intro/)》。

## 檔案結構

```
_quarto.yml            網站設定（導覽列、系列側欄、頁尾）
custom.scss            配色與版面樣式
index.qmd              首頁
about.qmd              關於
rdkit/index.qmd        《用 RDKit 玩化學》系列介紹頁
posts/<日期-主題>/      每篇文章一個資料夾：index.qmd、notebook、images/
_rdkit-play/           系列共用的網頁小框（RDKit.js）與產生備用圖、預覽圖的程式
_assets/               產生網站分享圖的程式
.github/workflows/     GitHub Actions：push 到 main 後自動建置並發布到 GitHub Pages
```

## 在本機預覽

需要 [Quarto](https://quarto.org/)（目前用 1.10.20）。

```bash
quarto preview
```

文章裡的程式碼不會在建置時執行，所以不需要安裝 Python 或 RDKit。只有重新產生圖片（`_rdkit-play/make_assets.py`、`make_cards.py`、`_assets/make_site_cards.py`）時才需要 RDKit 2026.9.1 與 Pillow。

## 授權

文章、圖片與 notebook 採用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh-hant)，引用時請註明「Cheninformatics《電腦也會化學》」。

有問題或發現錯誤，歡迎開 [issue](https://github.com/517justin/cheminfo-blog/issues)。
