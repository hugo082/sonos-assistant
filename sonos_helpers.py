#!/usr/bin/env python
import soco
import logging


USE_SONOS_IP = True
SONOS_IP = '192.168.1.24'


def search_sonos():
    zone_list = list(soco.discover())
    size = len(zone_list)
    if size == 0:
        logging.error('Sonos not found')
        raise Exception('Sonos not found')
    elif size > 1:
        logging.warning('Multi sonos room founded. Choose first index')
    return zone_list[0]


def get_sonos():
    if USE_SONOS_IP:
        return soco.SoCo(SONOS_IP)
    else:
        return search_sonos()


def main():
    sonos = get_sonos()

    sonos.play_uri('http://82.238.12.180:8080/out.wav')
    track = sonos.get_current_track_info()
    print(track['title'])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
