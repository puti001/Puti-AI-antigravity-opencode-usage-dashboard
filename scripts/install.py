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
        
        target_desktop = None
        for path in desktop_paths:
            if os.path.exists(path):
                target_desktop = path
                break
                
        if not target_desktop:
            target_desktop = home
            print("[Warning] Could not auto-detect standard Desktop folder. Creating shortcut in Home folder instead.")
            
        # 品牌 IP 識別前綴
        bat_path = os.path.join(target_desktop, "Puti-AI Antigravity Stats.bat")
        
        # 3. 取得當前 Python 對應的 pythonw.exe 絕對路徑
        pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = "pythonw"

        # 4. 寫入 bat 啟動檔 (使用 Python 腳本自帶的通訊埠 Toggle 機制)
        bat_content = f"""@echo off
rem Start or toggle the dashboard instance
start "" "{pythonw_path}" "{widget_path}"
"""
        
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
            
        print(f"[Success] Created Puti-AI desktop shortcut successfully!")
        print(f"Path: {bat_path}")
        print("You can now double-click this file on your desktop to launch/close the dashboard.")
        return True
        
    except Exception as e:
        print(f"[Error] Failed to install: {e}")
        return False

if __name__ == "__main__":
    print("Initializing Puti-AI Antigravity & OpenCode Usage Dashboard...")
    install()
    input("\nPress Enter to exit...")
