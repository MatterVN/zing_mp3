'''=== Play Top 100 or song name from Zing MP3 ===
   === Copy right 2019 by ttvtien
'''
import json, requests, time, random, datetime, hmac, hashlib, urllib, gzip, logging, os.path

from distutils.version import StrictVersion
from homeassistant.const import (
    ATTR_FRIENDLY_NAME, __version__ as current_ha_version)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'zing_mp3'
VERSION = '1.0.4'
VERSION_URL = ("https://raw.githubusercontent.com/MagnetVN/zing_mp3/{}/custom_components/zing_mp3/version.json")
REMOTE_BASE_URL = ("https://raw.githubusercontent.com/MagnetVN/zing_mp3/{}/custom_components/zing_mp3/")

COMPONENT_ABS_DIR = os.path.dirname(
    os.path.abspath(__file__))


#service data
CONF_PLAYER_ID = 'entity_id'
CONF_NAME = 'name'
CONF_CATEGORY= 'category'
CONF_REPEAT = 'repeat'
CONF_SHUFFLE = 'shuffle'

# const data
TOP100 = {'pop':'ZWZB96AB', 'country': 'ZWZB96AE', 'rock': 'ZWZB96AC', 'dance': 'ZWZB96C7', 'r&b': 'ZWZB96C8', 'rap': 'ZWZB96AD', 'soundtrack': 'ZWZB96C9',
          'nhac tre':'ZWZB969E', 'tru tinh': 'ZWZB969F', 'que huong': 'ZWZB96AU', 'cach mang': 'ZWZB96AO', 'rock viet': 'ZWZB96A0', 'rap viet': 'ZWZB96AI', 'dance viet': 'ZWZB96AW'}
url_list = 'https://mp3.zing.vn/xhr/media/get-list?op=top100&start=0&length=20&id='
url_audio = 'https://mp3.zing.vn/xhr/media/get-source?type=audio&key='
url_search  = "https://zingmp3.vn/api/search?"

prefix_url = 'https:'

API_KEY     = '38e8643fb0dc04e8d65b99994d3dafff'
SECRET_KEY  = b'10a01dcf33762d3a204cb96429918ff6'


#This function will get top 100 list
def get_codes_list(type_TOP):
    type_TOP = type_TOP.lower()
    uri = url_list + TOP100.get(type_TOP)
    re = requests.get(uri).json()
    items = re['data']['items']
    audio_codes = []
    for item in items:
        code = item['code']
        audio_codes.append(code)
    return audio_codes

def get_song_info(song_code):
    song_info = {}
    #codes = get_codes(type_TOP)
    #for code in codes:
    uri = url_audio + song_code
    re = requests.get(uri).json()['data']
    duration = int(re['duration'])
    source = re['source']
    link = prefix_url + source['128']
    song_info['duration'] = duration
    song_info['link'] = link
    return song_info

def setup(hass, config):
# Play top 100
    def play_top100(data_call):
        # Get data service
        media_id = data_call.data.get(CONF_PLAYER_ID,'media_player.apple_room_speaker')
        music_type  = data_call.data.get(CONF_CATEGORY, 'tru tinh')
        repeat = data_call.data.get(CONF_REPEAT, False)
        shuffle = data_call.data.get(CONF_SHUFFLE, False)
        # get playlist as code_list
        codes_list = get_codes_list(music_type)
        if (shuffle):
            codes_list = random.choices(codes_list, k=len(codes_list))
        # force stop media player
        # hass.services.call('media_player', 'media_stop', {'entity_id': media_id})
        ''' play '''
        continue_play = True
        i = 0
        while (continue_play):
            song_code = codes_list[i]
            song_info = get_song_info(song_code)
            # Call service from Home Assistant
            service_data = {'entity_id': media_id, 'media_content_id': song_info['link'], 'media_content_type': 'music'}
            hass.services.call('media_player', 'play_media', service_data)
            # sleep while media_player is playing
            time.sleep(song_info['duration'] - 2)
            if (hass.states.get(media_id).state == 'playing'):
                if (i < len(codes_list) - 1):
                    i = i + 1
                elif (repeat):
                    i = 0
                else:
                    continue_play = False
            else:
                continue_play = False





# ----------------------------------------------------------------------------------------------------------------------
# Play by song name
    def get_hash256(string):
        return hashlib.sha256(string.encode('utf-8')).hexdigest()

    def get_hmac512(string):
        return hmac.new(SECRET_KEY, string.encode('utf-8'), hashlib.sha512).hexdigest()

    def get_request_path(data):

        def mapping(key, value):
            return urllib.parse.quote(key) + "=" + urllib.parse.quote(value)

        data = [mapping(k, v) for k, v in data.items()]
        data = "&".join(data)

        return data

    def get_json_data(link):
        f = urllib.request.urlopen(link)
        gzipFile = gzip.GzipFile(fileobj=f)
        return json.loads(gzipFile.read().decode('utf-8'))

    def get_song_by_id(id):
        url = f"https://zingmp3.vn/api/song/get-song-info?id={id}&"
        time = str(int(datetime.datetime.now().timestamp()))
        sha256 = get_hash256(f"ctime={time}id={id}")

        data = {
            'ctime': time,
            'api_key': API_KEY,
            'sig': get_hmac512(f"/song/get-song-info{sha256}")
        }

        return url + get_request_path(data)

    def search_song(name):
        time = str(int(datetime.datetime.now().timestamp()))
        sha256 = get_hash256(f"ctime={time}")
        data = {
            'ctime': time,
            'api_key': API_KEY,
            'q': name,
            'start': '0',
            'count': '1',
            'type': 'song',
            'sig': get_hmac512(f"/search{sha256}")
        }

        response = get_json_data(f"{url_search}{get_request_path(data)}")
        #_LOGGER.warn("response: ", response)
        try:
            media_data = get_json_data(get_song_by_id(response['data']['items'][0]['id']))
            return f"https:{media_data['data']['streaming']['default']['128']}"
        except:
            return 'error'

    async def play_song(data_call):
        media_id = data_call.data.get(CONF_PLAYER_ID,'media_player.apple_room_speaker')
        mediaUrl = search_song(data_call.data.get(CONF_NAME, '0').lower())
        #_LOGGER.warn("mediaUrl: ", mediaUrl)
        service_data = {'entity_id': media_id, 'media_content_id': mediaUrl, 'media_content_type': 'music'}
        hass.services.call('media_player', 'play_media', service_data)

    async def _check_update(service):
        await _update(hass)

    async def _update_component(service):
        await _update(hass, True)

    hass.services.register(DOMAIN, 'play_top100', play_top100)
    hass.services.async_register(DOMAIN, 'play', play_song)
    hass.services.async_register(DOMAIN, 'check_update', _check_update)
    hass.services.async_register(DOMAIN, 'update_component', _update_component)

    return True
# ----------------------------------------------------------------------------------------------------------------------
async def _update(hass, do_update=False, notify_if_latest=True):
    try:
        request = requests.get(VERSION_URL, stream=True, timeout=10)
    except:
        _LOGGER.error("An error occurred while checking for updates. "
                      "Please check your internet connection.")
        return

    if request.status_code != 200:
        _LOGGER.error("Invalid response from the server while "
                      "checking for a new version")
        return

    data = request.json()
    last_version = data['version']
    min_ha_version = data['minHAVersion']
    release_notes = data['releaseNotes']

    if StrictVersion(last_version) <= StrictVersion(VERSION):
        if notify_if_latest:
            hass.components.persistent_notification.async_create(
                "You're already using the latest version!", title='Zing MP3')
        return

    if StrictVersion(current_ha_version) < StrictVersion(min_ha_version):
        hass.components.persistent_notification.async_create(
            "There is a new version of Zing MP3, but it is **incompatible** "
            "with your HA version. Please first update Home Assistant.", title='Zing MP3')
        return

    if do_update is False:
        hass.components.persistent_notification.async_create(
            release_notes, title='Zing MP3')
        return

    # Begin update
    files = data['files']
    has_errors = False

    for file in files:
        try:
            source = REMOTE_BASE_URL + file
            dest = os.path.join(COMPONENT_ABS_DIR, file)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            Helper.downloader(source, dest)
        except:
            has_errors = True
            _LOGGER.error("Error updating %s. Please update the file manually.", file)

    if has_errors:
        hass.components.persistent_notification.async_create(
            "There was an error updating one or more files of Zing MP3. "
            "Please check the logs for more information.", title='Zing MP3')
    else:
        hass.components.persistent_notification.async_create(
            "Successfully updated to {}. Please restart Home Assistant."
            .format(last_version), title='Zing MP3')

class Helper():
    @staticmethod
    def downloader(source, dest):
        req = requests.get(source, stream=True, timeout=10)

        if req.status_code == 200:
            with open(dest, 'wb') as fil:
                for chunk in req.iter_content(1024):
                    fil.write(chunk)
        else:
            raise Exception("File not found")