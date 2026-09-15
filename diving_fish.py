"""
从水鱼获取 b50 数据并生成 JiETNG 同款 UI 的图表格
必须与 main.py 在同一目录下运行
"""
from flask import Flask, request, jsonify, send_file, render_template_string
import requests
import random
import gc
from io import BytesIO

from modules.record_manager import get_detailed_info
from modules.maimai_manager import get_rating_image_path
from main import select_records, generate_profile
from modules.images.records import generate_records_picture
from modules.images.composition import compose_images

app = Flask(__name__)

QUERY_FORM_HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diving Fish B50 查询</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            max-width: 500px;
            width: 100%;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 8px;
            color: #333;
            text-align: center;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 15px;
            transition: all 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .button-group {
            display: flex;
            gap: 12px;
        }
        button {
            flex: 1;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .btn-primary:active {
            transform: translateY(0);
        }
        .divider {
            text-align: center;
            margin: 20px 0;
            color: #999;
            font-size: 14px;
        }
        .tips {
            background: #f8f9fa;
            padding: 16px;
            border-radius: 8px;
            margin-top: 24px;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }
        .tips strong {
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>JiETNG Best 50</h1>
        <p class="subtitle">使用 JiETNG 的图像生成模块生成您的国服 B50 成绩图</p>

        <form id="queryForm">
            <div class="form-group">
                <label for="username">水鱼用户名</label>
                <input type="text" id="username" name="username" placeholder="请输入水鱼用户名">
            </div>

            <div class="divider">或者</div>

            <div class="form-group">
                <label for="qq">QQ 号</label>
                <input type="text" id="qq" name="qq" placeholder="请输入 QQ 号">
            </div>

            <div class="button-group">
                <button type="submit" class="btn-primary">查询 B50</button>
            </div>
        </form>

        <div class="tips">
            <strong>💡 使用提示：</strong><br>
            • 输入水鱼用户名或 QQ 号中的任意一个即可<br>
            • 查询结果将显示为图片格式<br>
            • 数据来源于 Diving Fish API
        </div>
    </div>

    <script>
        document.getElementById('queryForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const qq = document.getElementById('qq').value.trim();

            if (!username && !qq) {
                alert('请至少输入用户名或QQ号！');
                return;
            }

            let url = '/?';
            if (username) {
                url += 'username=' + encodeURIComponent(username);
            } else if (qq) {
                url += 'qq=' + encodeURIComponent(qq);
            }

            window.location.href = url;
        });

        document.getElementById('username').addEventListener('input', function() {
            if (this.value) {
                document.getElementById('qq').value = '';
            }
        });
        document.getElementById('qq').addEventListener('input', function() {
            if (this.value) {
                document.getElementById('username').value = '';
            }
        });
    </script>
</body>
</html>
"""

def get_divingfish_data(username=None, qq=None):
    url = "https://www.diving-fish.com/api/maimaidxprober/query/player"

    if username:
        data = {
            "username": username,
            "b50": "1"
        }
    elif qq:
        data = {
            "qq": qq,
            "b50": "1"
        }
    else:
        return None, None

    headers = {
        "Content-Type": "application/json"
    }

    with requests.post(url, json=data, headers=headers) as response:
        if response.status_code != 200:
            return None, None
        raw_data = response.json()

    def clean_chart_data(chart, new_song=False):
        """清洗单个谱面数据"""
        return {
            "name": chart["title"],
            "type": chart["type"].lower().replace("sd", "std"),
            "score": f"{chart['achievements']:.4f}%",
            "difficulty": chart["level_label"].lower().replace(":", ""),
            "_ra": chart["ra"],
            "_internalLevelValue": chart["ds"],
            "score_icon": chart["rate"] if chart["rate"] else "back",
            "combo_icon": chart["fc"] if chart["fc"] else "back",
            "sync_icon": chart["fs"].replace("fsd", "fdx") if chart["fs"] else "back",
            "dx_score": "",
            "_new_song": new_song,
        }

    # 处理谱面数据
    cleaned_charts = []
    if "charts" in raw_data:
        for chart in raw_data["charts"]["dx"]:
            cleaned_charts.append(clean_chart_data(chart, True))
        for chart in raw_data["charts"]["sd"]:
            cleaned_charts.append(clean_chart_data(chart))

    charts = get_detailed_info(cleaned_charts)
    for chart in charts:
        chart["ra"] = chart["_ra"]
        chart["internalLevelValue"] = chart["_internalLevelValue"]
        chart["new_song"] = chart["_new_song"]
        del chart["_ra"]
        del chart["_internalLevelValue"]
        del chart["_new_song"]

    icon_urls = [
        "https://maimaidx.jp/maimai-mobile/img/Icon/33c162742808f6be.png",
        "https://maimaidx.jp/maimai-mobile/img/Icon/b6625e6726e92a13.png",
        "https://maimaidx.jp/maimai-mobile/img/Icon/1a3e72174eb86393.png",
        "https://maimaidx.jp/maimai-mobile/img/Icon/8ed59c0111ca92d6.png",
        "https://maimaidx.jp/maimai-mobile/img/Icon/921b3c1233700b70.png"
    ]
    nameplate_urls = [
        "https://maimaidx.jp/maimai-mobile/img/NamePlate/d1dd6f722d5c1121.png",
        "https://maimaidx.jp/maimai-mobile/img/NamePlate/427ce8b2e50e01c9.png",
        "https://maimaidx.jp/maimai-mobile/img/NamePlate/dd41aec14261fbac.png",
        "https://maimaidx.jp/maimai-mobile/img/NamePlate/a71e2f556c325853.png",
        "https://maimaidx.jp/maimai-mobile/img/NamePlate/85b6d4655374b56c.png"
    ]

    rating = raw_data.get('rating', 0)

    user_data = {
        "name": raw_data.get("nickname"),
        "rating": f"{rating}",
        "trophy_content": "JiETNG・カヰテー",
        "trophy_url": "https://maimaidx.jp/maimai-mobile/img/trophy_rainbow.png",
        "nameplate_url": random.choice(nameplate_urls),
        "icon_url": random.choice(icon_urls),
        "rating_block_path": get_rating_image_path(rating)
    }
    return user_data, charts


@app.route('/', methods=['GET'])
def query_player():
    try:
        username = request.args.get('username')
        qq = request.args.get('qq')

        if not username and not qq:
            return render_template_string(QUERY_FORM_HTML), 200

        user_data, charts = get_divingfish_data(username=username, qq=qq)

        if user_data is None:
            return jsonify({'error': 'Failed to fetch data from diving-fish'}), 500

        profile_img = generate_profile(user_data)
        up_songs, down_songs, _ = select_records(charts)
        record_img = generate_records_picture(up_songs, down_songs, "BEST50")
        img = compose_images([profile_img, record_img], timezone_offset=8)

        del profile_img, record_img
        gc.collect(0)

        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        del img
        gc.collect(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
