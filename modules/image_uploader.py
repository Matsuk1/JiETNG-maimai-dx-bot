import requests
from io import BytesIO
from PIL import Image

def _upload_to_uguu(img):
    url = "https://uguu.se/upload.php"

    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    files = {'files[]': ('image.png', img_io, 'image/png')}
    resp = requests.post(url, files=files)

    try:
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("files"):
                return data["files"][0]["url"]
            else:
                print("[uguu] 上传失败：", data)
        else:
            print("[uguu] 请求失败：", resp.status_code)
    except Exception as e:
        print("[uguu] 解析响应异常：", e)

    return None

def _upload_to_0x0(img):
    url = "https://0x0.st"

    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    files = {'file': ('image.png', img_io, 'image/png')}
    response = requests.post(url, files=files)

    try:
        if response.status_code == 200 and response.text.startswith("https://0x0.st/"):
            return response.text.strip()
        else:
            print("[0x0] 上传失败：", response.text)
    except Exception as e:
        print("[0x0] 异常：", e)

    return None

# 智能图床上传
def smart_upload(img):
    print("[smart_upload] 使用 uguu 上传")
    url = _upload_to_uguu(img)
    if url:
        return url

    print("[smart_upload] 切换 0x0 上传")
    url = _upload_to_0x0(img)
    if url:
        return url

    print("[smart_upload] 所有图床上传失败")
    return None
