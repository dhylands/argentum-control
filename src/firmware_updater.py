import requests
import json
import hashlib
import os, os.path

firmware_base_url = 'http://update.shiel.io/firmware/'
firmware_index = 'firmware.txt'

def update_firmware_list():
    download_file('firmware.txt', calculate_sha=False)

def parse_firmware_list(filename):
    f = open(filename, 'r')

    try:
        firmware_list = json.loads(f.read())
    except:
        return None

    return firmware_list

def get_all_firmware():
    return parse_firmware_list(firmware_index)

def get_available_firmware():
    all_firmware = get_all_firmware()

    available_firmware = []

    for firmware in all_firmware:
        if os.path.isfile(firmware['filename']):
            available_firmware.append(firmware)

    return available_firmware

def get_unavailable_firmware():
    all_firmware = get_all_firmware()

    unavailable_firmware = []

    for firmware in all_firmware:
        if not os.path.isfile(firmware['filename']):
            unavailable_firmware.append(firmware)

    return unavailable_firmware

def download_file(filename, calculate_sha=True):
    #local_filename = url.split('/')[-1]
    local_filename = filename
    url = '{}{}'.format(firmware_base_url, filename)

    r = requests.get(url, stream=True)

    hasher = hashlib.sha1()

    if r.ok:
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    if calculate_sha:
                        hasher.update(chunk)

                    f.write(chunk)
                    f.flush()

        file_sha = hasher.hexdigest()

        return file_sha

    return None

def update_local_firmware():
    firmware_list = get_unavailable_firmware()

    for firmware in firmware_list:
        result = download_file(firmware['filename'])

        if not result:
            print('Download failed.')
        else:
            if result != firmware['sha']:
                print('Hash check failed')
                os.remove(firmware['filename'])


if __name__ == '__main__':
    update_firmware_list()

    update_local_firmware()

    available_firmware = get_available_firmware()

    print('Available firmware versions:')

    for firmware in available_firmware:
        print(firmware['version'])
