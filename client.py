import requests
import base64
import time

url = 'http://10.61.212.13:5000/display'

with open('/home/d/Pictures/proto/photo_test.png', 'rb') as f1:
    f1_bytes = f1.read()

with open('/home/d/Pictures/license_plate.jpg', 'rb') as f2:
    f2_bytes = f2.read()


for i in range(10):
    data = {
        "status": "OK",
        "message": "xin chào các bạn",
        "lane_id": "R",
        "is_landscape": "1",
        "title": str(i),
        "profile_image": base64.b64encode(f1_bytes),
        "license_plate_image": base64.b64encode(f2_bytes)
    }
    print(i)
    requests.post(url, data=data)
    time.sleep(2)

