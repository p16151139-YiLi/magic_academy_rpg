# Magic Academy: The Lost Ancient Magic

2D 像素風魔法學院 RPG 專案。此 ZIP 是整理後的 Python 原始專案，不是可直接雙擊執行的 Windows 遊戲，也不是已重新 Build 的 GitHub Pages 網頁包。

## 開發環境

```bash
pip install pygame-ce pygbag
```

## 本機／Colab 網頁建置

在專案根目錄執行：

```bash
pygbag --build .
```

網頁輸出位於 `build/web/`。將該資料夾內的內容部署至 GitHub Pages 的發布來源。

## 主要資料夾

- `scenes/`：遊戲場景
- `systems/`：玩家、職業、地圖、背包及成長系統
- `ui/`：玩家選單、角色資訊及背包介面
- `data/`：職業、玩家存檔、地圖及設定 JSON
- `assets/`：圖片、字型、角色及地圖素材

## 注意

- 三種職業的資料與選擇流程已保留。
- 近戰型與遠程型角色目前暫時共用均衡型法師的動畫精靈圖，使用色調區分；待取得專屬精靈圖後可替換。
- 教室、圖書館及森林的背景圖片尚未包含在目前素材中。
- 具體修正與未完成素材清單請見 `docs/INTEGRATION_REPORT.md`。
