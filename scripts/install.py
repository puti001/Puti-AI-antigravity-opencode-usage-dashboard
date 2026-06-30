# -*- coding: utf-8 -*-
import os
import sys

def install():
    try:
        # 1. 取得當前 widget 腳本的絕對路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        widget_path = os.path.join(current_dir, "opencode_widget.py")
        
        if not os.path.exists(widget_path):
            print(f"[Error] Cannot find widget script at: {widget_path}")
            return False
            
        # 2. 定義可能的桌面路徑
        home = os.path.expanduser("~")
        desktop_paths = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "OneDrive", "桌面"),
        ]
        
        target_desktops = []
        for path in desktop_paths:
            if os.path.exists(path):
                target_desktops.append(path)
                
        if not target_desktops:
            target_desktops = [home]
            print("[Warning] Could not auto-detect standard Desktop folder. Creating shortcut in Home folder instead.")
            
        # 3. 取得當前 Python 對應的 pythonw.exe 絕對路徑
        pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = "pythonw"

        # 4. 寫入 bat 啟動檔 (使用 Python 腳本自帶的 PID 檔案鎖 Toggle 機制)
        bat_content = f"""@echo off
rem Start or toggle the dashboard instance
start "" "{pythonw_path}" "{widget_path}"
"""
        
        for desktop in target_desktops:
            bat_path = os.path.join(desktop, "Puti-AI Antigravity Stats.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            print(f"[Success] Created Puti-AI desktop shortcut successfully at: {bat_path}")
            
        return True
        
    except Exception as e:
        print(f"[Error] Failed to install: {e}")
        return False

if __name__ == "__main__":
    print("Initializing Puti-AI Antigravity & OpenCode Usage Dashboard...")
    install()
    input("\nPress Enter to exit...")
