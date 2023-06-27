import discord
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import ssl
from commands import add_movie, list_movies, find_movie, update_year, \
    delete_movie

load_dotenv()

# Initialize client object (the "bot")
intents = discord.Intents.default()
client = discord.Client(intents=intents)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URI = os.getenv('MONGODB_URI')

# Connect to MongoDB Atlas cluster using URI from .env file.
mongo_client = MongoClient(MONGO_URI)

# Replace "test" with the name of your database in MongoDB Atlas cluster.
db_name = 'movies'
db = mongo_client[db_name]

# Replace "movies" with the name of your collection within the database.
collection_name = 'movies_collection'
collection = db[collection_name]

context = ssl.create_default_context(cafile="cert.pem")
context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check for specific commands and execute corresponding function.

    if message.content.startswith('!addmovie'):
        params_list = message.content.split(" ")
        result_str = add_movie(params_list[1], params_list[2], params_list[3])

        await message.channel.send(result_str)

    elif message.content.startswith('!listmovies'):
        result_str = list_movies()

        await message.channel.send(result_str)

    elif message.content.startswith('!findmovie'):
        params_list = message.content.split(" ")
        result_str = find_movie(params_list[1])

        await message.channel.send(result_str)

    elif message.content.startswith('!updateyear'):
        params_list = message.content.split(" ")
        result_str = update_year(params_list[1], params_list[2])

        await message.channel.send(result_str)

    elif message.content.startswith('!deletemovie'):
        params_list = message.content.split(" ")
        result_str = delete_movie(params_list[1])

        await channel.send(result_string)


# Run the bot using its unique authentication token
client.run(DISCORD_TOKEN, ssl=context)