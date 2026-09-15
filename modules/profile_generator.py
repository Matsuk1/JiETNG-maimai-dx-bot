from modules.image_skins import skinnable
"""Render profile nameplates using HTML while keeping the existing asset requests."""
import logging
from io import BytesIO

import requests
from PIL import Image

from modules.html_renderer import file_uri, image_uri, render_template

logger = logging.getLogger(__name__)


@skinnable
def generate_profile_image(user_info, scale=1, rounded_icon=False):
    assets = {}
    for key in ('nameplate_url', 'icon_url', 'rating_block_url', 'class_rank_url', 'cource_rank_url', 'trophy_url'):
        if key == 'rating_block_url' and user_info.get('rating_block_path'):
            continue
        url = user_info.get(key)
        if not url:
            continue
        headers = None
        if url.startswith('https://maimaidx-eng.com'):
            headers = {
                'Referer': 'https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                'Host': 'maimaidx-eng.com',
            }
        try:
            with requests.get(url, headers=headers, verify=False, timeout=(5, 20)) as response:
                response.raise_for_status()
                with Image.open(BytesIO(response.content)) as source:
                    with source.convert('RGB' if key == 'nameplate_url' else 'RGBA') as image:
                        assets[key] = image_uri(image)
        except (requests.RequestException, OSError, ValueError) as exc:
            logger.warning('[Image] Failed to load profile asset: key=%s, error=%s', key, exc)
    rating_path = user_info.get('rating_block_path')
    if rating_path:
        assets['rating_block_path'] = file_uri(rating_path)
    return render_template('profile.html', int(1363 * scale), int(218 * scale),
                           user=user_info, assets=assets, scale=scale, rounded_icon=rounded_icon,
                           rating=str(user_info['rating']).rjust(5))
