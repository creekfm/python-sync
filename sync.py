# -*- coding: utf-8 -*-

# basic os functions
import os

# logging
import logging
from logging.handlers import RotatingFileHandler

# scheduling imports
import time
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# connecting to the website - get next show
import urllib.request

# json parsing - get next show
import json

# yaml parsing - config
import yaml

# MP3 tag editing
from mutagen.id3 import ID3NoHeaderError, ID3v1SaveOptions
from mutagen.id3 import ID3, TIT2, TALB, TPE1

__author__ = 'forrest'


# TODO: configuration file
# TODO: email on directory creation (new show - won't play)
# TODO: daemonize
# TODO: Auto Rerun (second to last show in podcast RSS)


# main function
def download_files():
    logger.name = 'bff.download_files'
    logger.info("Starting process")

    # Config params
    destination_folder = config["destination_folder"]
    station_url = config["station_url"]
    key = config["key"]

    # download json
    upcoming_url = "api/broadcasts/upcoming?key="
    full_upcoming_url = station_url + upcoming_url + key
    logger.debug("Upcoming broadcast URL: " + full_upcoming_url)
    response = urllib.request.urlopen(full_upcoming_url)
    str_response = response.read().decode('utf-8')
    logger.debug("string response: " + str_response)
    broadcasts = json.loads(str_response)
    logger.debug("json response: ")
    logger.debug(broadcasts)

    start_time = broadcasts[0]['start']
    logger.debug("Next Broadcast at " + start_time)

    # time calculation
    showtime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    now_plus_10 = datetime.datetime.now() + datetime.timedelta(minutes=10)
    # initialize possibly empty value
    remote_path = ""
    # if the show will start in the next 10 minutes
    if showtime <= now_plus_10:
        logger.debug("Found a show that will start in 10 minutes")

        show_id = broadcasts[0]['show_id']
        logger.debug("show id: " + show_id)

        title = broadcasts[0]['title']
        logger.debug("Title: " + title)

        show_media = broadcasts[0]['media']
        for media in show_media:
            subtype = media.get('subtype', 'no key found')
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
        str_response = response.read().decode('utf-8')
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
        local_filename = os.path.join(destination_folder, short_name, short_name + "-newest.mp3")
        logger.debug('Local Filename: ' + local_filename)

        # create directories, if needed
        local_directory = os.path.dirname(local_filename)
        if not os.path.exists(local_directory):
            logger.warning('Had to make directory ' + local_directory)
            os.makedirs(local_directory)

        if remote_path:
            # download file
            logger.info("Downloading " + remote_path + " to " + local_filename)
            with urllib.request.urlopen(remote_path) as response, open(local_filename, 'wb') as out_file:
                data = response.read()  # get binary data
                out_file.write(data)  # write binary (open 'wb')
            logger.info("download complete.")
        else:
            logger.warn("No file was attached to the broadcast!")

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

            logger.debug("Removing tags")
            tags.delete(local_filename)
            logger.debug("Saving tags")
            # v1=2 switch forces ID3 v1 tag to be written
            tags.save(filename=local_filename,
                      v1=ID3v1SaveOptions.CREATE,
                      v2_version=4)

    else:
        # show time is not 10 minutes or less from now
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            show_delta = showtime - datetime.datetime.now()
            s = show_delta.seconds
            days, hour_rem = divmod(s, 86400)
            hours, remainder = divmod(hour_rem, 3600)
            minutes, seconds = divmod(remainder, 60)
            show_delta_string = "{0} days, {1} hours, {2} minutes, {3} seconds".format(days, hours, minutes, seconds)
            short_name = broadcasts[0]['Show']['short_name']
            logger.debug("Next show (" + short_name + ") in " + show_delta_string + ", not running download step yet")

    logger.info("Finished process")
    logger.name = __name__


if __name__ == '__main__':
    # MAIN PROCESS

    with open('pysync-config.yml', 'r') as f:
        config = yaml.load(f)

    # prep logging system
    log_path = config["log_path"]
    log_file_name = config["log_name"]
    log_level = config["log_level"]

    log_format = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # log to file
    log_file_handler = RotatingFileHandler(filename="{0}/{1}.log".format(log_path, log_file_name),
                                           maxBytes=10 * 1024 * 1024,  # 10 MB
                                           backupCount=20)
    log_file_handler.setFormatter(log_format)
    logger.addHandler(log_file_handler)

    # log to console
    log_console_handler = logging.StreamHandler()
    log_console_handler.setFormatter(log_format)
    logger.addHandler(log_console_handler)

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
