"""
Tip/Ad 管理模块
用于管理update完成后显示的提示和广告信息
"""

import json
import os
import random
import logging
from datetime import datetime
from modules.config_loader import TIP_AD_FILE

logger = logging.getLogger(__name__)

# 全局变量
TIP_AD_DATA = []
_ENABLED_TIPS = []  # 缓存启用的 tip 列表
_ENABLED_ADS = []   # 缓存启用的 ad 列表


def _rebuild_cache():
    """重建启用的 tip/ad 缓存"""
    global _ENABLED_TIPS, _ENABLED_ADS

    _ENABLED_TIPS = [
        item for item in TIP_AD_DATA
        if item.get('enabled', True) and item.get('type') == 'tip'
    ]
    _ENABLED_ADS = [
        item for item in TIP_AD_DATA
        if item.get('enabled', True) and item.get('type') == 'ad'
    ]

    logger.debug(f"[TipAd] Cache rebuilt: {len(_ENABLED_TIPS)} tips, {len(_ENABLED_ADS)} ads")


def load_tip_ad_data():
    """
    加载tip/ad数据

    Returns:
        list: tip/ad数据列表
    """
    global TIP_AD_DATA

    try:
        if os.path.exists(TIP_AD_FILE):
            with open(TIP_AD_FILE, 'r', encoding='utf-8') as f:
                TIP_AD_DATA = json.load(f)
                logger.info(f"[TipAd] Loaded {len(TIP_AD_DATA)} tip/ad items from {TIP_AD_FILE}")
        else:
            # 创建默认数据文件
            TIP_AD_DATA = []
            save_tip_ad_data()
            logger.info(f"[TipAd] Created new tip/ad data file at {TIP_AD_FILE}")
    except Exception as e:
        logger.error(f"[TipAd] Failed to load tip/ad data: {e}", exc_info=True)
        TIP_AD_DATA = []

    # 重建缓存
    _rebuild_cache()

    return TIP_AD_DATA


def save_tip_ad_data():
    """
    保存tip/ad数据到文件

    Returns:
        bool: 是否保存成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(TIP_AD_FILE), exist_ok=True)

        with open(TIP_AD_FILE, 'w', encoding='utf-8') as f:
            json.dump(TIP_AD_DATA, f, ensure_ascii=False, indent=2)

        logger.info(f"[TipAd] Saved {len(TIP_AD_DATA)} tip/ad items to {TIP_AD_FILE}")

        # 重建缓存
        _rebuild_cache()

        return True
    except Exception as e:
        logger.error(f"[TipAd] Failed to save tip/ad data: {e}", exc_info=True)
        return False


def get_all_tip_ads():
    """
    获取所有tip/ad数据

    Returns:
        list: 所有tip/ad数据
    """
    return TIP_AD_DATA.copy()


def get_random_tip():
    """
    随机获取一个启用的tip

    Returns:
        dict: 随机选择的tip数据，如果没有启用的则返回None
    """
    if not _ENABLED_TIPS:
        return None

    return random.choice(_ENABLED_TIPS)


def get_random_ad():
    """
    随机获取一个启用的ad

    Returns:
        dict: 随机选择的ad数据，如果没有启用的则返回None
    """
    if not _ENABLED_ADS:
        return None

    return random.choice(_ENABLED_ADS)


def create_tip_ad(tip_type, text_zh, text_en, text_ja, button_type=None, button_label_zh=None,
                   button_label_en=None, button_label_ja=None, button_value=None, enabled=True):
    """
    创建新的tip/ad

    Args:
        tip_type: 类型 ('tip' 或 'ad')
        text_zh: 中文文本
        text_en: 英文文本
        text_ja: 日文文本
        button_type: 按钮类型 ('uri' 或 'message')，None表示无按钮
        button_label_zh: 按钮中文标签
        button_label_en: 按钮英文标签
        button_label_ja: 按钮日文标签
        button_value: 按钮值（URI或消息文本）
        enabled: 是否启用

    Returns:
        dict: 创建的tip/ad数据
    """
    tip_ad = {
        'id': str(len(TIP_AD_DATA) + 1),
        'type': tip_type,
        'text': {
            'zh': text_zh,
            'en': text_en,
            'ja': text_ja
        },
        'enabled': enabled,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 如果有按钮
    if button_type and button_value:
        tip_ad['button'] = {
            'type': button_type,
            'label': {
                'zh': button_label_zh or '',
                'en': button_label_en or '',
                'ja': button_label_ja or ''
            },
            'value': button_value
        }

    TIP_AD_DATA.append(tip_ad)
    save_tip_ad_data()

    logger.info(f"[TipAd] Created new {tip_type}: id={tip_ad['id']}")
    return tip_ad


def update_tip_ad(tip_id, tip_type=None, text_zh=None, text_en=None, text_ja=None,
                  button_type=None, button_label_zh=None, button_label_en=None,
                  button_label_ja=None, button_value=None, enabled=None, remove_button=False):
    """
    更新tip/ad

    Args:
        tip_id: tip/ad ID
        tip_type: 类型
        text_zh: 中文文本
        text_en: 英文文本
        text_ja: 日文文本
        button_type: 按钮类型
        button_label_zh: 按钮中文标签
        button_label_en: 按钮英文标签
        button_label_ja: 按钮日文标签
        button_value: 按钮值
        enabled: 是否启用
        remove_button: 是否移除按钮

    Returns:
        dict: 更新后的tip/ad数据，如果未找到则返回None
    """
    for tip_ad in TIP_AD_DATA:
        if tip_ad['id'] == tip_id:
            if tip_type is not None:
                tip_ad['type'] = tip_type

            if text_zh is not None:
                tip_ad['text']['zh'] = text_zh
            if text_en is not None:
                tip_ad['text']['en'] = text_en
            if text_ja is not None:
                tip_ad['text']['ja'] = text_ja

            if enabled is not None:
                tip_ad['enabled'] = enabled

            # 处理按钮
            if remove_button:
                tip_ad.pop('button', None)
            elif button_type and button_value:
                tip_ad['button'] = {
                    'type': button_type,
                    'label': {
                        'zh': button_label_zh or '',
                        'en': button_label_en or '',
                        'ja': button_label_ja or ''
                    },
                    'value': button_value
                }

            tip_ad['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_tip_ad_data()

            logger.info(f"[TipAd] Updated tip/ad: id={tip_id}")
            return tip_ad

    logger.warning(f"[TipAd] Tip/ad not found: id={tip_id}")
    return None


def delete_tip_ad(tip_id):
    """
    删除tip/ad

    Args:
        tip_id: tip/ad ID

    Returns:
        bool: 是否删除成功
    """
    global TIP_AD_DATA

    original_length = len(TIP_AD_DATA)
    TIP_AD_DATA = [tip for tip in TIP_AD_DATA if tip['id'] != tip_id]

    if len(TIP_AD_DATA) < original_length:
        save_tip_ad_data()
        logger.info(f"[TipAd] Deleted tip/ad: id={tip_id}")
        return True

    logger.warning(f"[TipAd] Tip/ad not found for deletion: id={tip_id}")
    return False


def get_tip_ad_by_id(tip_id):
    """
    根据ID获取tip/ad

    Args:
        tip_id: tip/ad ID

    Returns:
        dict: tip/ad数据，如果未找到则返回None
    """
    for tip_ad in TIP_AD_DATA:
        if tip_ad['id'] == tip_id:
            return tip_ad.copy()

    return None
