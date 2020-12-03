import requests
import base64

url = 'http://10.61.212.13:5000/display'

with open('/home/d/Pictures/proto/photo_test.png', 'rb') as f1:
    f1_bytes = f1.read()

with open('/home/d/Pictures/license_plate.jpg', 'rb') as f2:
    f2_bytes = f2.read()

data = {
    "status" : "STOP",
    "message": "sfgfdgfghghghgfdgdgdfgdfg",
    "lane_id": "R",
    "is_landscape": "1",
    "title": "title",
    "profile_image": base64.b64encode(f1_bytes),
    "license_plate_image": base64.b64encode(f2_bytes)
}

requests.post(url, data=data)