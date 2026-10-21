"""
Maimai 纯工具函数

不依赖网络、aiohttp 或 lxml 的纯计算/解析函数，从 maimai_manager.py 中分离。
"""

import logging
import os
import re
import unicodedata

from modules.config_loader import RATING_DIR

logger = logging.getLogger(__name__)

RATING_TIERS = [
    (16750, "rainbow_extreme_4.png"),
    (16500, "rainbow_extreme_3.png"),
    (16250, "rainbow_extreme_2.png"),
    (16000, "rainbow_extreme_1.png"),
    (15750, "rainbow_4.png"),
    (15500, "rainbow_3.png"),
    (15250, "rainbow_2.png"),
    (15000, "rainbow_1.png"),
    (14750, "platinum_2.png"),
    (14500, "platinum_1.png"),
    (14250, "gold_2.png"),
    (14000, "gold_1.png"),
    (13000, "silver.png"),
    (12000, "bronze.png"),
    (10000, "purple.png"),
    (7000,  "red.png"),
    (4000,  "yellow.png"),
    (2000,  "green.png"),
    (1000,  "blue.png"),
    (0,     "white.png"),
]


def get_rating_image_path(rating: int) -> str:
    for threshold, filename in RATING_TIERS:
        if rating >= threshold:
            return os.path.join(RATING_DIR, filename)
    return os.path.join(RATING_DIR, "white.png")


def parse_level_value(input_str):
    input_str = input_str.strip()

    if '.' in input_str:
        try:
            return [float(input_str)]
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a float number with point(.): {input_str}")
            return None

    elif input_str.endswith('+'):
        try:
            base = int(input_str[:-1])
            target = [round(base + i * 0.1, 1) for i in range(6, 10)]
            return target
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a number with plus(+): {input_str}")
            return None

    else:
        try:
            base = int(input_str)
            return [round(base + i * 0.1, 1) for i in range(6)]
        except ValueError:
            logger.error(f"[Maimai] ✗ Failed to parse a number: {input_str}")
            return None


def normalize(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("　", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()
