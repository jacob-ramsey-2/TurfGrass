import upnpclient  # Replace ssdp with upnpclient
import requests

def discover_camera():
    devices = upnpclient.discover()  # Discover UPnP devices
    for device in devices:
        # Check if the device matches the Sony Camera service
        if 'urn:schemas-sony-com:service:Camera:1' in device.location:
            camera_ip = device.location.split('//')[1].split(':')[0]
            return camera_ip
    return None

def get_available_apis(camera_ip):
    url = f'http://{camera_ip}:8080/api'
    data = {'method': 'getAvailableApiList', 'id': 1, 'jsonrpc': '2.0'}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json().get('result', {}).get('apis', [])
    else:
        return []

def call_api(camera_ip, method, params={}):
    url = f'http://{camera_ip}:8080/api'
    data = {'method': method, 'params': params, 'id': 1, 'jsonrpc': '2.0'}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        return None

if __name__ == "__main__":
    camera_ip = discover_camera()
    if camera_ip:
        print(f'Camera IP: {camera_ip}')
        apis = get_available_apis(camera_ip)
        print('Available APIs:')
        print(apis)
        
        # Example: take a picture
        result = call_api(camera_ip, 'takePicture')
        if result:
            print('Picture taken successfully')
        else:
            print('Failed to take picture')
    else:
        print('No camera found')