__author__ = 'forrest'

# basic os functions
import os
# logging
import logging
# scheduling imports
import time
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# connecting to the website - get next show
import urllib
# json parsing - get next show
import json

# MP3 tag editing
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import ID3, TIT2, TALB, TPE1


# main function
def download_files():
    logger.name = 'bff.download_files'
    logger.info("Starting process")

    # Config params
    destination_folder = "C:/temp/audio"
    station_url = "http://creek.fm/"
    key = "##########"

    # download json
    upcoming_url = "api/broadcasts/upcoming?key="
    full_upcoming_url = station_url + upcoming_url + key
    logger.debug("Upcoming broadcast URL: " + full_upcoming_url)
    response = urllib.request.urlopen(full_upcoming_url)
    str_response = response.readall().decode('utf-8')
    logger.debug("string response: " + str_response)
    broadcasts = json.loads(str_response)
    logger.debug("json response: ")
    logger.debug(broadcasts)

    start_time = broadcasts[0]['start']
    logger.debug("Next Broadcast at " + start_time)

    # time calculation
    showtime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    now_plus_10 = datetime.datetime.now() + datetime.timedelta(minutes=10)
    # if the show will start in the next 10 minutes
    if showtime <= now_plus_10:
        logger.debug("Found a show that will start in 10 minutes")

        show_id = broadcasts[0]['show_id']
        logger.debug("show id: " + show_id)

        title = broadcasts[0]['title']
        logger.debug("Title: " + title)

        show_media = broadcasts[0]['media']
        for media in show_media:
            subtype = media['subtype']
            logger.debug("Media subtype: " + subtype)
            if subtype == 'mp3':
                logger.debug("found an mp3: ")
                remote_path = media['url']
                logger.debug("Remote Path: " + remote_path)

        # get show metadata
        logger.debug("getting show information")
        show_url = "api/show/"
        full_show_url = station_url + show_url + show_id
        logger.debug("Show URL: " + full_show_url)
        response = urllib.request.urlopen(full_show_url)
        str_response = response.readall().decode('utf-8')
        logger.debug("string response: " + str_response)
        show_info = json.loads(str_response)
        logger.debug("json response: ")
        logger.debug(show_info)

        album = show_info['title']
        logger.debug("Show Name (album): " + album)

        short_name = show_info['short_name']
        logger.debug("Short Name (local folder): " + short_name)

        # iterate through hosts
        logger.debug("trying to get hosts")
        hosts = show_info['hosts']
        host_list = []
        for host in hosts:
            logger.debug("Found a host")
            host_list.append(host['display_name'])

        if len(host_list) > 1:
            logger.debug("making a list of hosts for Artist field")
            artist = ','.join(host_list)
        else:
            logger.debug("Only one host")
            artist = host_list[0]
        logger.debug("Hosts (artist): " + artist)

        # construct filename
        local_filename = os.path.join(destination_folder, short_name, short_name + "-" + start_time[0:10] + ".mp3")
        logger.debug("Local Filename: " + local_filename)

        # create directories, if needed
        local_directory = os.path.dirname(local_filename)
        if not os.path.exists(local_directory):
                logger.warning("Had to make directory " + local_directory)
                os.makedirs(local_directory)

        # download file
        logger.info("Downloading " + remote_path + " to " + local_filename)
        with urllib.request.urlopen(remote_path) as response, open(local_filename, 'wb') as out_file:
            data = response.read()  # get binary data
            out_file.write(data)    # write binary (open 'wb')
        logger.info("download complete.")

        # add mp3 tags
        if os.path.exists(local_filename):
            # set mp3 tags
            logger.debug("Adding mp3 tag")
            try:
                tags = ID3(local_filename)
            except ID3NoHeaderError:
                logger.debug("Adding ID3 header")
                tags = ID3()
            logger.debug("Constructing tag")
            # title
            tags["TIT2"] = TIT2(encoding=3, text=title)
            # album
            tags["TALB"] = TALB(encoding=3, text=album)
            # artist
            tags["TPE1"] = TPE1(encoding=3, text=artist)

            logger.debug("Saving tag")
            # v1=2 switch forces ID3 v1 tag to be written
            tags.save(local_filename, v1=2)

        # schedule, if needed

    logger.info("Finished process")
    logger.name = __name__

if __name__ == '__main__':
    # MAIN PROCESS
    # prep logging system
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("Program Start")

    # background scheduler is part of apscheduler class
    scheduler = BackgroundScheduler()
    # add a cron based (clock) scheduler for every 30 minutes, 20 minutes past
    scheduler.add_job(download_files, 'cron', minute='20,50')
    scheduler.start()

    logger.info('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible

    logger.info("Program Stop")