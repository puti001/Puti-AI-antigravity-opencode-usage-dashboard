# [Puti-AI] Antigravity and OpenCode Usage Dashboard | Antigravity 與 OpenCode 使用額度與 Token 監控面板

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一個專為 **Antigravity (Gemini Models)** 與 **OpenCode (open call / open chord / opencode.ai)** 設計的電腦端懸浮桌面監控小面板。

---

## 💡 聲明與致謝 (Reference & Credits)

本專案之設計靈感與概念源自於以下開源專案，特此標註並致以最誠摯的尊重：
* **參考專案 (Reference Repository)**: [frankchiu-dev/claude-codex-usage-dashboard](https://github.com/frankchiu-dev/claude-codex-usage-dashboard)
* **原創作者**: @frankchiu-dev

我們在此開源專案的基礎上，針對 **Antigravity** 與 **OpenCode** 的 API 限額與計費特性進行了全新的 UI 設計與功能重構，提供了 Win11 原生圓角與圓環進度圈 (Progress Ring) 的高級視覺體驗。

---

## ✨ 核心特色

1. **🎨 頂級現代美學**：
   * **Win11 原生圓角與邊框陰影**：完美契合 Windows 現代設計風格。
   * **響應式圓環進度圈 (Progress Ring)**：將數據優雅呈現於圓環內，數字大字置中，百分符號置於正下方，資訊乾淨清爽。
2. **📱 雙分頁對稱限額監控**：
   * **Tab 1: Antigravity**：監控 `Gemini Models`（5小時 / 每週）與 `Claude and GPT models` 的雲端限額。
   * **Tab 2: OpenCode**：監控 `OpenCode Go` 的額度消耗（滾動 / 每週 / 每月限額）以及本地 Session / Cost 數據。
3. **📐 八向邊緣與角落縮放**：
   * 滑鼠移到面板的任何邊界或角落即可直接拖曳縮放，字體大小與進度環尺寸會等比例響應式縮放！
4. **🔄 一鍵即時重新整理**：
   * 右上角配有手動更新按鈕，點擊立刻呼叫本地 `opencode stats`。
5. **🔑 右鍵手動設定額度，強大同步**：
   * 右鍵選單支援「設定初始額度 (Set Limits)」，隨時輸入網頁後台數字進行 100% 同步！

---

## 🛠️ 安裝與啟動

### 1. 複製本專案到本地
```bash
git clone https://github.com/puti001/Puti-AI-antigravity-opencode-usage-dashboard.git
cd antigravity-opencode-usage-dashboard
```

### 2. 執行安裝程式一鍵建立桌面捷徑
```bash
python scripts/install.py
```
執行後，程式會自動檢測你的 Windows 桌面路徑，並為你建立一個 **`Puti-AI Antigravity Stats.bat`** 捷徑。

### 3. 使用方法
* **啟動 / 關閉**：雙擊桌面上的 `Puti-AI Antigravity Stats.bat`。點選第一次為「啟動」，再點選一次即為「關閉」。
* **拖曳移動**：滑鼠左鍵按住面板內部空白處即可隨意拖曳移動。
* **拖曳縮放**：滑鼠移到面板的邊界或四個角落，下游標變為雙向箭頭後，按住左鍵即可任意調整大小。
* **右鍵選單**：在面板上點擊滑鼠右鍵，可進行手動整理、手動微調額度（輸入 `Gemini5H, GeminiWk, OpenCodeMo` 百分比）、或結束程式。

---

## 📝 授權條款 (License)

本專案採用 [MIT 授權條款](LICENSE) 開源。
