# weather.py
# Discord bot geocodes placename in user message and retrieves weather data and imagery from National Weather Service API based on radar station code.
# Created by Marcus Perry May 8, 2022
from genericpath import exists
import discord, os, requests, json, datetime, errno
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
#         return False
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
            # Discord caches embeds by URL, so vary URL each time to refresh when a request for a radar station is repeated.
                embed_URL = "https://radar.weather.gov/ridge/lite/{0}_loop.gif?{1}".format(radar_code, date_url)
                embed.set_image(url=embed_URL)
                message_load = "Current forecast and most recent regional radar for "+str.title(arg)+" ("+coords+"):"+"\n"+">>> "+current+"\n"
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

bot.run(DISCORD_TOKEN, bot=True)



