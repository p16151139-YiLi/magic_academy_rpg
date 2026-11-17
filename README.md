# Magic Academy: The Lost Ancient Magic — V9.8.2

## 本版重點
- 以 V9.8.1 R1 完整專案為基礎，保留原有遊戲系統、7 張地圖、16 位 NPC、獨立家具、椅子、碰撞、場景切換及 UI。
- 修正三項舊 SDL 回歸測試與目前遊戲架構不一致的問題：獨立家具圖層、坐姿 NPC 專用素材、圖書館新版分段家具碰撞。
- Colab 上傳以專案內容 SHA256 驗證，不再依賴瀏覽器上傳檔名；可接受 R1 後綴或瀏覽器自動附加的副本名稱。
- Pygbag 建置前檢查完整 runtime 檔案引用，建置後逐項核對 APK/TAR 內的來源雜湊。
- Colab 真實 SDL 測試產生七張地圖的執行畫面聯絡表及完整截圖 ZIP。
- 更新版本標籤、release manifest、Colab Notebook 與測試文件，避免版本資訊不一致。

## 遊戲內容保留
- 7 張地圖、16 位 NPC、15 個四方向圖集與 1 個 seated-only NPC profile。
- 3 個實際坐姿 NPC placement；坐姿角色使用專用 PNG，站立/漫遊角色使用四方向圖集。
- 課桌、閱讀桌、書櫃、椅子、櫃台、水晶台、盆栽等獨立透明 PNG 物件。
- 獨立家具座標、深度排序、分段碰撞與椅子座位保留。
- 玩家移動、地圖切換、NPC AI、對話、商店、背包、裝備、技能/角色 UI、快捷列及存檔資料。

## 測試
- 固定 55 項回歸測試：40 項非 SDL、15 項真實 Pygame/SDL。
- 測試清單、分類、每項 timeout 與完整錯誤彙總均固定。
- Colab 必須達成 55 PASS、0 FAIL、0 SKIP、0 preflight error，並產生至少 56 張真實 SDL 截圖。
- Pygbag build、GitHub push 與 Pages 公開 APK SHA256 驗證均為後續必要關卡。

## Colab 部署
使用 `Magic_Academy_RPG_V9_8_2_Colab_Final_Audit_Deploy.ipynb`，上傳 `Magic_Academy_RPG_V9_8_2_Full_Project_Audited.zip`。Notebook 會驗證 ZIP 完整性及專案內容 SHA256，不以檔名作為唯一判斷。
