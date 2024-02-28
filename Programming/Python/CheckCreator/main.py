"""
Check Creators Availability

Author: Amir Sarrafzadeh Arasi
Date: 2024-02-28

Purpose:
This script is going to check the availability of the creators and if they are available, it will insert the data into the table.

Process:
1. Import the required libraries.
2. Create a custom formatter to add the line number to the log.
3. Define the getToken function to get the token from the ArcGIS Portal.
4. Define the getRecords function to get the records from the table.
5. Create a custom logger and configure it with the custom formatter.
6. Read the config file.
7. Connect to the ArcGIS Portal and get the creator licences.
8. Create a FastAPI app.
9. Create a post method to check the availability of the creators and insert the data into the database.
10. Create a post method to check the availability of the creators.

Notes:
1. This script is for development purposes and the credentials should be checked before using it in the production environment.
2. The config file should be in the same directory as the main.py file.
"""

# Import the required libraries
import os
import sys
import json
import logging
import uvicorn
import requests
import configparser
import datetime as dt
from arcgis.gis import GIS
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse


# Create a custom formatter to add the line number to the log
class LineNumberFormatter(logging.Formatter):
    def format(self, record):
        # Get the line number of the calling frame
        record.lineno = getattr(record, 'lineno', 'unknown')
        return super().format(record)


# Define the getToken function to get the token from the ArcGIS Portal
def getToken(url: str, tokenUser: str, tokenPassword: str, tokeExpiration: int): # -> str
    # Define the data to get the token
    tokenData = {
        'username': tokenUser,
        'password': tokenPassword,
        'referer': '.',
        'expiration': tokeExpiration,
        'f': 'json'
    }

    # Make a POST request to get the token
    tokenResponse = requests.post(url, data=tokenData)

    # Parse the response to get the token
    tokenResult = tokenResponse.json()['token']
    return tokenResult


# Define the getRecords function to get the not expired records from the table
def getRecords(featureServiceURL: str): # -> int
    # Get the token
    queryToken = getToken(tokenURL, username, password, expiration)

    # Define the URL to delete the expired records
    deleteURL = featureServiceURL + '/' + 'deleteFeatures'
    deleteData = {
        'where': f"end_ < CURRENT_TIMESTAMP",
        'f': 'json'
    }
    deleteUrlWithToken = f'{deleteURL}?token={queryToken}'
    deleteResponse = requests.post(deleteUrlWithToken, data=deleteData)
    if deleteResponse.status_code == 200:
        logger.info("The expired records have been deleted successfully.")
        # Define the URL to query the table
        queryURL = featureServiceURL + '/' + 'query'
        queryData = {
            'where': '1=1',
            'outFields': '*',
            'returnGeometry': 'false',
            'f': 'json'
        }

        queryUrlWithToken = f'{queryURL}?token={queryToken}'
        queryResponse = requests.post(queryUrlWithToken, data=queryData)
        queryResult = queryResponse.json()['features']
        return len(queryResult)
    else:
        logger.error("Error deleting the expired records: " + str(deleteResponse.json()))
        sys.exit()


app = FastAPI()
router = APIRouter()

class Item(BaseModel):
    ID: str
    username: str = None

# Create a post method to check the availability of the creators and insert the data into the database
@app.post("/add")
async def create_item(item: Item):
    # Get the not expired records from the table
    records = getRecords(tableURL)
    if creatorLicences <= records:
        return {"ID": item.ID, "creator": item.username, "status": "failed",
                "message": "No creator licences available"}
    else:
        now = datetime.now().timestamp() * 1000
        end = now + (duration * 60000)

        try:
            token = getToken(tokenURL, username, password, expiration)
            logger.info("The token has been received successfully.")
        except Exception as ex:
            logger.error("Error getting token: " + str(ex))
            sys.exit()

        # Make a POST request to add a new feature
        add_feature_url = f"{tableURL}/addFeatures?token={token}"

        # Define the payload (data to be sent)
        payload = {
            "features": json.dumps([
                {
                    "attributes": {
                        "id": item.ID,
                        "user_": item.username,
                        "start": now,
                        "end_": end
                    }
                }
            ]),
            "gdbVersion": "",
            "rollbackOnFailure": True,
            "timeReferenceUnknownClient": False,
            "f": "json"
        }

        response = requests.post(add_feature_url, data=payload)
        if response.status_code == 200:
            logger.info("The feature has been added successfully.")
            dateNow = dt.datetime.fromtimestamp(now/1000).strftime('%Y-%m-%d %H:%M:%S')
            endNow = dt.datetime.fromtimestamp(end/1000).strftime('%Y-%m-%d %H:%M:%S')
            return {"ID": item.ID, "creator": item.username, "start": dateNow, "end": endNow, "remaining (minutes)": f"{duration}", "status": "success",
                    "message": "remaining creator licences: " + str(creatorLicences - records - 1)}
        else:
            logger.error("Error adding feature: " + str(response.json()))
            return {"ID": item.ID, "creator": item.username, "status": "failed", "message": "Failed to add feature"}


@app.post("/check")
async def check():
    try:
        checkRecords = getRecords(tableURL)
        logger.info("The table has been checked successfully.")
    except Exception as ex:
        logger.error("Error getting features from the table: " + str(ex))
        sys.exit()

    if creatorLicences > checkRecords:
        return {"status": "success", "licences": f"{creatorLicences - checkRecords}", "message": f"there exist {creatorLicences - checkRecords} remaining creator licences."}
    else:
        return {"status": "failed", "licences": "0", "message": "No creator licences available"}

# Include a route to serve the Swagger UI
# http://localhost:8000/docs
@router.get("/docs", include_in_schema=False, response_class=HTMLResponse)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

# Mount the router to the main app
app.include_router(router)

# Define the function to generate OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="GeoWorks API",
        version="1.0.0",
        description="This is a simple API to check the availability of the creators and insert the data into the database.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Include the OpenAPI schema route
app.openapi = custom_openapi



if __name__ == '__main__':

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

    # Read config file
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        config.read(config_path)
        portalURL = config['credentials']['portalURL']
        tokenURL = config['credentials']['tokenURL']
        username = config['credentials']['username']
        password = config['credentials']['password']
        tableURL = config['credentials']['tableURL']
        duration = int(config['credentials']['duration'])
        expiration = int(config['credentials']['expiration'])
        logger.info("Config file read successfully")
    except Exception as e:
        logger.error("Error reading config file: " + str(e))
        sys.exit()

    # Connect to the ArcGIS Portal and get the creator licences
    try:
        gis = GIS(portalURL, username, password)
        logger.info("The connection to the ArcGIS Portal has been established successfully.")

        userTypes = gis.admin.system.licenses.properties['userTypes']
        creatorLicences = 0
        for userType in userTypes:
            if userType['id'] == 'creatorUT':
                print(userType)
                creatorLicences = int(userType['maximumRegisteredMembers']) # 'currentRegisteredMembers'
                logger.info(f"The portal {portalURL} has {creatorLicences} creator licences.")
                break
    except Exception as ex:
        logger.error("Error connecting to ArcGIS Portal: " + str(ex))
        sys.exit()


    uvicorn.run(app, host="0.0.0.0", port=8000)
