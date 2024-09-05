import discord
import aiohttp
import certifi
import ssl
import random
import requests
from tmdbv3api import TMDb
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.server_api import ServerApi

from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME, TMDB_API_KEY, DISCORD_BOT_TOKEN


client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
db = client[DATABASE_NAME][COLLECTION_NAME]


tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY

# Create the aiohttp client session with the SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None

    async def setup_hook(self) -> None:
        # Create the aiohttp client session with the SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))

    async def close(self):
        await self.session.close()
        await super().close()
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    # helpful for debugging and to see user input
    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

        # Check if the message is a command to store one or more movies in MongoDB
        if message.content.startswith('!addmovie'):
            # Extract the movie names from the message and split them by asterisks (*)
            movie_names = message.content.replace('!addmovie ', '').split('*')

            # Loop through each movie name and insert it into MongoDB
            for movie_name in movie_names:
                # Remove leading and trailing whitespaces
                movie_name = movie_name.strip()

                # Insert the movie into MongoDB
                insert_movie(movie_name)

                # Send a custom message for each movie added
                await message.channel.send(f'Movie "{movie_name}" has been added to the list!')


        # Check if the message is a command to list all movies
        elif message.content == '!listmovies':
            movies = list_movies()
            if movies:
                await message.channel.send(f'Movies:\n{movies}')
            else:
                await message.channel.send('No movies found in the list.')

        # Check if the message is a command to update a movie
        elif message.content.startswith('!updatemovie'):
            # Extract movie name and updated name from the message
            content = message.content.split()
            if len(content) >= 3:
                movie_name = content[1]
                updated_name = ' '.join(content[2:])
                update_movie(movie_name, updated_name)
                await message.channel.send(f'Movie "{movie_name}" updated to "{updated_name}".')



        if message.content.startswith('!deletemovie'):
            # Extract movie name from the message
            movie_name = message.content.replace('!deletemovie ', '')

            # Check if the movie exists before attempting to delete it
            if movie_exists(movie_name):
                delete_result = delete_movie(movie_name)
                await message.channel.send(delete_result)
            else:
                await message.channel.send(f'Movie "{movie_name}" not found in the list.')

        if message.content.startswith('!deleteall'):
            deleted_count = delete_all_movies()
            await message.channel.send(f'{deleted_count} movies have been deleted.')

        # Think about adding multiple dice at once
        if message.content.startswith('!roll'):
            # Roll for # of times of logic in !roll original
            try:
                # Extract the number of sides from the message
                sides = int(message.content.replace('!roll', ''))

                if sides <= 0:
                    await message.channel.send("The number of sides must be greater than 0.")
                else:
                    result = random.randint(1, sides)
                    await message.channel.send(f"You rolled a {sides}-sided dice and got: {result}")
            except ValueError:
                await message.channel.send("Invalid input. Use !roll followed by the number of sides (e.g., !roll 6).")

        if message.content.startswith('!randommovie'):
            random_movie = select_random_movie()
            if random_movie:
                await message.channel.send(random_movie)
            else:
                await message.channel.send('No movies found.')

def select_random_movie():
    # Count the number of movies in the collection
    movie_count = db.movies.count_documents({})

    if movie_count == 0:
        return "No movies found."

    # Generate a random index
    random_index = random.randint(0, movie_count - 1)

    # Fetch a random movie document
    random_movie = db.movies.find().limit(1).skip(random_index).next()

    # Format the movie details
    movie_details = (
        f"Randomly selected movie:\n"
        f"Name: {random_movie.get('name', 'N/A')}\n"
        f"Title: {random_movie.get('title', 'N/A')}\n"
        f"Release Year: {random_movie.get('release_year', 'N/A')}\n"
        f"Where to Watch: {', '.join(random_movie.get('where_to_watch_services', ['N/A']))}\n"
        f"Rating: {random_movie.get('rating', 'N/A')}"
    )

    return movie_details



def movie_exists(movie_name):
    # Perform a case-insensitive search for the movie name
    result = db.movies.find_one({'name': {'$regex': f'^{movie_name}$', '$options': 'i'}})
    return result is not None

#add the streaming services when inserting into the movie list to save api calls
#to improve response time and performance at the reduction of timely accuracy


def insert_movie(movie_name):

    try:
        # Capitalize the movie name while excluding certain words
        capitalized_name = capitalize_movie_name(movie_name)
        existing_movie = db.movies.find_one({'name': capitalized_name})

        if existing_movie:

            return (capitalized_name, "already exists. Try another movie.")
        # Search for the movie using the TMDb API
        tmdb_search_url = f'https://api.themoviedb.org/3/search/movie?api_key={tmdb.api_key}&query={capitalized_name}'
        response = requests.get(tmdb_search_url)

        if response.status_code == 200:
            movie_data = response.json()
            if movie_data['results']:

                result = movie_data['results'][0]

                # Extract relevant information
                movie_title = result['title']
                release_year = result['release_date'][:4]  # Get the first 4 characters for the year
                rating = result['vote_average']  # Include the rating

                # Use the movie's TMDB ID to fetch external IDs, including "where to watch" data
                tmdb_id = result['id']

                # services are provided by JustWatch
                where_to_watch_services = get_where_to_watch_services(tmdb_id)

                # Insert the movie into MongoDB with streaming service names, rating, and US streaming services
                db.movies.insert_one({
                    'name': capitalized_name,
                    'title': movie_title,  # Include the title
                    'release_year': release_year,  # Include the release year
                    'where_to_watch_services': where_to_watch_services,  # Store streaming service names as a list
                    'rating': rating,  # Include the rating
                })

            else:
                # (Implied) movie not found in TMDb
                db.movies.insert_one({'name': capitalized_name})  # Use capitalized name here
    except DuplicateKeyError:
        pass


def get_where_to_watch_services(tmdb_id):
    streaming_providers = []
    try:
        tmdb_watch_providers_url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers?api_key={tmdb.api_key}'
        response = requests.get(tmdb_watch_providers_url)

        if response.status_code == 200:
            providers_data = response.json()

            # Check if 'US' region data exists in the response
            if 'results' in providers_data:

                results_data = providers_data['results']
                if 'US' in results_data:
                    us_data = results_data['US']

                    # Check if 'flatrate' exists in 'US' data
                    if 'flatrate' in us_data:
                        flatrate_providers = us_data['flatrate']

                        # Iterate through 'flatrate' providers and collect 'provider_name'
                        for provider in flatrate_providers:
                            provider_name = provider.get('provider_name')
                            if provider_name:
                                streaming_providers.append(provider_name)

                    return streaming_providers

            return []  # Return an empty list if no streaming services are found for the US region
        else:
            print(f"Error fetching 'where to watch' information. Status code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching 'where to watch' information: {e}")
        return []


def list_movies():
    movies = db.movies.find().sort('name', 1)  # Sort by 'name' field in ascending order
    movie_list = []

    for movie in movies:
        movie_name = movie['name']
        movie_title = movie.get('title', 'N/A')
        release_year = movie.get('release_year', 'N/A')
        where_to_watch_services = movie.get('where_to_watch_services', [])
        rating = movie.get('rating', 'N/A')

        # Create a single line with movie details
        movie_details = f"Name: {movie_name}\nTitle: {movie_title}\nRelease Year: {release_year}\nWhere to Watch Services: {', '.join(where_to_watch_services)}\nRating: {rating}\n"

        movie_list.append(movie_details)

    return '\n'.join(movie_list)  # Separate movies with double line breaks





def update_movie(movie_name, updated_name):
    db.movies.update_one({'name': movie_name}, {'$set': {'name': updated_name}})

def delete_all_movies():
    x = db.movies.delete_many({})
    deleted_count = x.deleted_count
    print(f'{deleted_count} movies deleted.')
    return deleted_count

def delete_movie(movie_name):
    try:
        # Perform a case-insensitive search for the movie name
        result = db.movies.delete_one({'name': {'$regex': f'^{movie_name}$', '$options': 'i'}})

        if result.deleted_count == 0:
            return f'Movie "{movie_name}" not found in the list.'
        else:
            return f'Movie "{movie_name}" deleted from the list.'
    except DuplicateKeyError:
        return 'An error occurred while deleting the movie.'



excluded_words = ['the', 'to', 'a']

def capitalize_movie_name(movie_name):
    # Split the movie name into words
    words = movie_name.split()

    # Capitalize the first word
    if words:
        words[0] = words[0].capitalize()

    # Capitalize other words unless they are in the excluded list
    # this is like some leetcode answer somewhere I bet
    for i in range(1, len(words)):
        if words[i].lower() not in excluded_words:
            words[i] = words[i].capitalize()

    # Join the words back into a single string
    return ' '.join(words)

# Intents setup
intents = discord.Intents.default()
intents.message_content = True

# Create and run the client
client = MyClient(intents=intents)
client.run(DISCORD_BOT_TOKEN)



async def main():
    async with MyClient(intents=intents) as client:
        await client.start(DISCORD_BOT_TOKEN)

# Run the bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
