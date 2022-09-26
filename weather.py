# weather2.py
# Discord bot geocodes placename in user message and retrieves weather data and imagery from National Weather Service API based on radar station code.
# Created by Marcus Perry May 8, 2022
# Updated Sept 12, 2022
# This branch of weather.py includes functionality for displaying base radial wind velocities from the NOAA NWS NEXRAD GeoServer
from genericpath import exists
from urllib.request import URLopener
import discord, os, requests, json, datetime, errno, tarfile, math
from json import JSONDecodeError
from discord.ext import commands

from dotenv import load_dotenv
from os.path import join, dirname
from dotenv import load_dotenv

# Create date/time variable for updating weather via unique URL
date_var = datetime.datetime.now()
date_url = date_var.strftime("%d"+"%m"+"%y"+"%M")


# Load tokens from .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("GUILD_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
# AGOL_TOKEN can be used to authenticate custom geocoding service or additional layers from ArcGIS Online when upgrading bot
# AGOL_TOKEN = os.environ.get("AGOL_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Set up image embed for geocoded search result
embed = discord.Embed()
embed.set_image(url="")

# EPSG 3857 conversion section modified from OP PolyGeo on gis.stackexchange:
radius = 6378137.0 # Earth's radius in meters at equator
def lon2x(webMercLong):
  longX = math.radians(webMercLong)*radius
  xrd = round(longX, 1)
  return xrd
def lat2y(webMercLat):
  longY = math.log(math.tan(math.pi / 4 + math.radians(webMercLat) / 2))*radius
  yrd = round(longY, 1)
  return yrd
# end^


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

# AGOL URL example for further customization 
# myURL = "https://geocode-api.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&singleLine={}&outFields=location&token=".format(arg)+AGOL_TOKEN

# This key is only present in the weather.gov json response if the location is not a valid US location.
success_key = 'success'

# Part of error handling testing for when forecast.weather.gov site redirects to marine.weather.gov, placename is invalid, and other issues as they arise.
# def valid_json(vj):
#     try:
#         json.dumps(vj)
#     except ValueError:
#         return False
#     except TypeError:
#     return True

@bot.command()
async def weather(weather, *, arg):
    myURL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&singleLine={}&outFields=location".format(arg)
    api_response = requests.get(myURL)
    response_json = api_response.json()
    loc_dict = response_json["candidates"][0]
    loc_dict2 = loc_dict["location"]
    loc_x = round(loc_dict2["x"], 2)
    loc_y = round(loc_dict2["y"], 2)
    coords = str(loc_x)+","+str(loc_y)
    gov_url = "https://forecast.weather.gov/MapClick.php?lat={0}&lon={1}&FcstType=json".format(loc_y,loc_x)
    # Create date/time variable for updating weather via unique URL
    date_var = datetime.datetime.now()
    date_url = date_var.strftime("%d%m%y%H%M")
    try:
        gov_response = requests.get(gov_url, allow_redirects=False)
        if gov_response.status_code == 200:
            gov_response_json = gov_response.json() 
            if success_key in gov_response_json:
                await weather.send("Location not found. Try again with US place name or correct the spelling.")    
            else:    
                radar_code = gov_response_json["location"]["radar"]
                current_list = gov_response_json["data"]["text"]
                current = current_list.pop(0)
                nowTemp = gov_response_json["currentobservation"]["Temp"]
                nowHum = gov_response_json["currentobservation"]["Relh"]
                nowSky = gov_response_json["currentobservation"]["Weather"]
                nowMsg = "It is currently {0}, {1}ºF with a relative humidity of {2}.".format(nowSky, nowTemp, nowHum)
            # Discord caches embeds by URL, so vary URL each time to refresh when a request for a radar station is repeated.
                embed_URL = "https://radar.weather.gov/ridge/lite/{0}_loop.gif?{1}".format(radar_code, date_url)
                embed.set_image(url=embed_URL)
                message_load = nowMsg+"\n"+">>> "+"Forecast and most recent regional radar for "+str.title(arg)+"("+coords+"):"+"\n"+"\n"+current+"\n"+"\n"
                await weather.send(message_load)
                await weather.send(embed=embed) 
        else:
            await weather.send("Redirect error: Try a place further inland.")     
    except errno.errorcode(): 
        await weather.send("JSONDecodeError.")
    except KeyError:
        await weather.send("Location not found. Try again with US place name or correct the spelling.")
    except Exception as e:
        await weather.send("unknown exception:{}".format(e))

@bot.command()
async def wind(wind, *, arg):
    myURL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&singleLine={}&outFields=location".format(arg)
    api_response = requests.get(myURL)
    response_json = api_response.json()
    loc_dict = response_json["candidates"][0]
    loc_dict2 = loc_dict["location"]
    loc_x = round(loc_dict2["x"], 2)
    loc_y = round(loc_dict2["y"], 2)
    ddX = lon2x(loc_x)
    ddY = lat2y(loc_y)
    # May need to change ranges if using different EPSG or units.
    # bbox_xmin = ddX-5
    # bbox_xmax = ddX+5
    # bbox_ymin = ddY-5
    # bbox_ymax = ddY+5
    bbox_xmin = loc_x-3
    bbox_xmax = loc_x+3
    bbox_ymin = loc_y-3
    bbox_ymax = loc_y+3
    coords = str(ddX)+","+str(ddY)
    # Additional steps would be required if getting archived imagery 
    # [radar_code]_tif = tarfile.open('')
    now = datetime.datetime.now()
    nowURL = now.isoformat()
    dotURL = r'%2f'
    gov_url = "https://forecast.weather.gov/MapClick.php?lat={0}&lon={1}&FcstType=json".format(loc_y,loc_x)
    try:
        gov_response = requests.get(gov_url, allow_redirects=False)
        if gov_response.status_code == 200:
            gov_response_json = gov_response.json() 
            if success_key in gov_response_json:
                await wind.send("Location not found. Try again with US place name or correct the spelling.")    
            else:    
                radar_codeOG = (gov_response_json["location"]["radar"])
                radar_code = radar_codeOG.lower()
                current_list = gov_response_json["data"]["text"]
                current = current_list.pop(0)
                nowWind = gov_response_json["currentobservation"]["Wind"]
            # Discord caches embeds by URL, so vary URL each time to refresh when a request for a radar station is repeated.
                base_URL = "https://opengeo.ncep.noaa.gov/geoserver/{}/ows".format(radar_code)
                layerlist = "{0}_bvel_raw".format(radar_code)
                # %2C{0}_bref_raw
                bbox_all = "{0}%2C{1}%2C{2}%2C{3}".format(bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax)
                epsg = r'EPSG%3A4326'
                params = "?SERVICE=WMS&REQUEST=GetMap&FORMAT=image/png&LAYERS={0}&WIDTH=512&HEIGHT=512&BBOX={1}&SRS={2}&TRANSPARENCY=true".format(layerlist, bbox_all, epsg)
                embed_URL = base_URL+params
                # uncomment for debug: print(embed_URL)
                embed.set_image(url=embed_URL)
                message_load = "Current wind speed: " + nowWind +" and Super Resolution Base [wind] Velocity (BVEL) for "+str.title(arg)+""+"\n"+">>> "+"\n"
                await wind.send(message_load)
                await wind.send(embed=embed) 
        else:
            await wind.send("Redirect error: Try a place further inland.")     
    except errno.errorcode(): 
       await wind.send("JSONDecodeError.")
    except KeyError:
        await wind.send("Location not found. Try again with US place name or correct the spelling.")
    except Exception as e:
        await wind.send("unknown exception:{}".format(e))

bot.run(DISCORD_TOKEN, bot=True)
