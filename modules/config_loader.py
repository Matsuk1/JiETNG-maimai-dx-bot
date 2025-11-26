"""
配置加载模块 - Telegram Bot 简化版
"""

import os

# 路径配置
FONT_PATH = "./assets/fonts/mplus-jietng.ttf"
LOGO_PATH = "./assets/pics/logo.jpg"
COVERS_DIR = "./data/covers"

# 图标路径
ICON_BASE_DIR = "./assets/icon"
ICON_TYPE_DIR = os.path.join(ICON_BASE_DIR, "type")
ICON_SCORE_DIR = os.path.join(ICON_BASE_DIR, "score")
ICON_DX_STAR_DIR = os.path.join(ICON_BASE_DIR, "dx_star")
ICON_COMBO_DIR = os.path.join(ICON_BASE_DIR, "combo")
ICON_SYNC_DIR = os.path.join(ICON_BASE_DIR, "sync")

# 确保目录存在
for directory in [COVERS_DIR, ICON_TYPE_DIR, ICON_SCORE_DIR, ICON_DX_STAR_DIR, ICON_COMBO_DIR, ICON_SYNC_DIR]:
    os.makedirs(directory, exist_ok=True)
