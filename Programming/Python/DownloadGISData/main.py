"""
Countries GIS Data

Author: Amir Sarrafzadeh Arasi
Date: 2024-02-23

Purpose:
Download the data for each country from the given URL and save it in the countries' folder.

Process:
1. Import the necessary libraries
2. Record the start time and create a custom logger
3. Read the Config.ini file
4. Generate the dictionary of countries
5. Download the data for each country
6. Record the end time and calculate the elapsed time

Notes:
1. The Config.ini file contains the URL, codes, and files and must be in the same directory as the script
2. The URL is the base URL for the data
"""

# Import the necessary libraries
import os
import sys
import time
import logging
import requests
import pycountry
import configparser

# Generate a dictionary of countries
def generate_countries_dict():
    countries_dict = {}
    for country in pycountry.countries:
        countries_dict[country.alpha_3] = country.name
    return countries_dict

# Create a custom formatter to add the line number to the log
class LineNumberFormatter(logging.Formatter):
    def format(self, record):
        # Get the line number of the calling frame
        record.lineno = getattr(record, 'lineno', 'unknown')
        return super().format(record)

if __name__ == '__main__':

    # Record the start time
    start_time = time.time()

    # Create a custom logger and configure it with the custom formatter
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a file handler and set the formatter and save the logs in the file.log file
    handler = logging.FileHandler("file.log")
    formatter = LineNumberFormatter('%(levelname)s | %(asctime)s | Line %(lineno)s | %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("All the setting of the logging is done correctly.")

    # Read Config.ini file
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        url = config['config']['url']
        codes = config['config']['codes'].split(',')
        files = config['config']['files'].split(',')
        logger.info("Config.ini file is read successfully.")
    except Exception as e:
        logger.error(f"There is an error: {e} in reading the config.ini file.")
        sys.exit(1)

    # Generate the dictionary of countries
    try:
        countries = generate_countries_dict()
        logger.info("Countries dictionary is generated successfully.")
    except Exception as e:
        logger.error(f"There is an error: {e} in generating the countries dictionary.")
        sys.exit(1)

    # Download the data for each country
    try:
        for key, value in countries.items():
            for i in range(len(codes)):
                tempUrl = url + codes[i] + f'/{key}_{codes[i]}.zip'
                response = requests.get(tempUrl)
                if response.status_code == 200:
                    tempFolderName = 'countries/' + value
                    if not os.path.exists(tempFolderName):
                        os.makedirs(tempFolderName)

                    with open(f'countries/{value}/{files[i]}.zip', 'wb') as f:
                        f.write(response.content)

                    logger.info(f"**{value} {codes[i]} data downloaded successfully**")
                else:
                    logger.info(f"$$Failed to download {value} {codes[i]} data$$")
    except Exception as e:
        logger.error(f"There is an error: {e} for downloading the data.")
        sys.exit(1)


    # Record the end time
    end_time = time.time()

    # Calculate the elapsed time
    elapsed_time = end_time - start_time
    logger.info(f"The operation time of the script was {elapsed_time/60} minutes.")






