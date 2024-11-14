import requests

baseUrl = "http://172.104.176.201:82/angkort/api/v1/product/category"

response = requests.post(baseUrl, json={})

print(response.text)