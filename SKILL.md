---
name: antigravity-opencode-usage-dashboard
description: Antigravity and OpenCode Usage Dashboard | Antigravity 與 OpenCode 使用額度與 Token 監控面板技能。幫助使用者與 Agent 監控本機的 token 使用量與限額，支援桌面無邊框懸浮圓環小面板。
---

# Antigravity and OpenCode Usage Dashboard | Antigravity 與 OpenCode 使用額度與 Token 監控面板

本技能可用於幫助使用者在電腦上部署一個極其精美的 Tkinter 懸浮 Dashboard 面板，用於監控 **Antigravity** 與 **OpenCode** 的 5小時/每週/每月額度限制與 Token 消耗。

## 📖 參考致謝 (Reference Credits)
本專案靈感與設計概念參考自開源專案 [frankchiu-dev/claude-codex-usage-dashboard](https://github.com/frankchiu-dev/claude-codex-usage-dashboard)，原作者 @frankchiu-dev。

## 🤖 Agent 執行指南 (For Agent Usage)

當使用者提出「看額度」、「監控使用量」或「懸浮小面板」需求時，Agent 可以執行以下步驟：

1. **取得本地統計資料**：
   執行 `opencode stats` 或讀取 `~/.local/share/opencode/opencode.db` 取得當前會話與花費數據。
2. **部署懸浮面板**：
   * 將 `scripts/opencode_widget.py` 複製到使用者的本機目錄（例如 `~/.gemini/antigravity/scratch/`）。
   * 執行 `scripts/install.py` 自動在桌面為使用者建立 `.bat` 啟動開關捷徑。
3. **引導說明**：
   告知使用者直接在桌面雙擊批次檔即可啟動，並說明手動微調、拖曳移動與邊緣縮放等高階功能。
