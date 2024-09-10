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

excluded_words = ['the', 'to', 'a']

def capitalize_movie_name(movie_name):
    # Split the movie name into words
    words = movie_name.split()

    # Capitalize the first word
    if words:
        words[0] = words[0].capitalize()

    # Capitalize other words unless they are in the excluded list
    for i in range(1, len(words)):
        if words[i].lower() not in excluded_words:
            words[i] = words[i].capitalize()

    # Join the words back into a single string
    return ' '.join(words)

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self.prefix = "!" # Default prefix
        self.db = db  # Store the database connection in the instance

    async def set_prefix(self, message, new_prefix):
        if new_prefix:
            self.prefix = new_prefix
            await message.channel.send(f"Prefix has been set to: {self.prefix}")
        else:
            await message.channel.send(
                "Please provide a new prefix. Usage: !setprefix <new_prefix>")

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
        if message.author == self.user:
            return

        print(f'Message from {message.author}: {message.content}')

        if message.content.startswith(self.prefix):
            command = message.content[len(self.prefix):].split()[0].lower()
            content = message.content[len(self.prefix) + len(command) + 1:]

            if command == 'setprefix':
                await self.set_prefix(message, content)
            elif command == 'help':
                await self.show_help(message)
            elif command == 'addmovie':
                await self.add_movie(message, content)
            elif command == 'listmovies':
                await self.list_movies(message)
            elif command == 'updatemovie':
                await self.update_movie(message, content)
            elif command == 'deletemovie':
                await self.delete_movie(message, content)
            elif command == 'deleteall':
                await self.delete_all_movies(message)
            elif command == 'roll':
                await self.roll_dice(message, content)
            elif command == 'randommovie':
                await self.random_movie(message)

    async def show_help(self, message):
        help_text = (
            f"Current prefix is: {self.prefix}\n"
            "Available commands:\n"
            f"{self.prefix}setprefix <new_prefix> - Set a new command prefix\n"
            f"{self.prefix}addmovie <movie_name> - Add a movie to the list\n"
            f"{self.prefix}deletemovie <movie_name> - Remove a movie from the list\n"
            f"{self.prefix}updatemovie <old_name> <new_name> - Update a movie's name\n"
            f"{self.prefix}listmovies - See the current movie list\n"
            f"{self.prefix}deleteall - Remove all movies from the list\n"
            f"{self.prefix}roll <number> - Roll a dice with the specified number of sides\n"
            f"{self.prefix}randommovie - Get a random movie from the list\n"
            f"{self.prefix}help - Show this help message"
        )
        await message.channel.send(help_text)

    async def add_movie(self, message, content):
        movie_names = content.split('*')
        # added list to store added movies because I've been getting leetcodey lately
        added_movies = []
        for movie_name in movie_names:
            movie_name = movie_name.strip()
            result = self.insert_movie(movie_name)
            if isinstance(result, tuple):
                await message.channel.send(f'Movie "{result[0]}" {result[1]}')
            else:
                added_movies.append(movie_name)
        if added_movies:
            await message.channel.send(f'Movies added to the list: {", ".join(added_movies)}')

    async def list_movies(self, message):
        movies = self.list_movies_from_db()
        if movies:
            # Create a formatted string for each movie
            movie_strings = []
            for movie in movies:
                movie_string = (
                    f"Name: {movie['name']}\n"
                    f"Title: {movie['title']}\n"
                    f"Release Year: {movie['release_year']}\n"
                    f"Where to Watch Services: {', '.join(movie['where_to_watch_services'])}\n"
                    f"Rating: {movie['rating']}\n\n"
                )
                movie_strings.append(movie_string)

            # Split the message into chunks
            max_length = 2000  # Discord's max message length
            chunks = []
            current_chunk = ""
            for movie_string in movie_strings:
                if len(current_chunk) + len(movie_string) > max_length:
                    chunks.append(current_chunk)
                    current_chunk = movie_string
                else:
                    current_chunk += movie_string
            if current_chunk:
                chunks.append(current_chunk)

            # Send each chunk as a separate message
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send('No movies found in the list.')

    async def update_movie(self, message, content):
        parts = content.split(maxsplit=1)
        if len(parts) >= 2:
            movie_name = parts[0]
            updated_name = parts[1]
            self.update_movie_in_db(movie_name, updated_name)
            await message.channel.send(f'Movie "{movie_name}" updated to "{updated_name}".')
        else:
            await message.channel.send("Invalid format. Use: !updatemovie <old_name> <new_name>")

    async def delete_movie(self, message, content):
        movie_name = content.strip()
        if self.movie_exists(movie_name):
            delete_result = self.delete_movie_from_db(movie_name)
            await message.channel.send(delete_result)
        else:
            await message.channel.send(f'Movie "{movie_name}" not found in the list.')

    async def delete_all_movies(self, message):
        deleted_count = self.delete_all_movies_from_db()
        await message.channel.send(f'{deleted_count} movies have been deleted.')

    async def roll_dice(self, message, content):
        try:
            sides = int(content)
            if sides <= 0:
                await message.channel.send("The number of sides must be greater than 0.")
            else:
                result = random.randint(1, sides)
                await message.channel.send(f"You rolled a {sides}-sided dice and got: {result}")
        except ValueError:
            await message.channel.send("Invalid input. Use !roll followed by the number of sides (e.g., !roll 6).")

    async def random_movie(self, message):
        random_movie = self.select_random_movie()
        if random_movie:
            await message.channel.send(random_movie)
        else:
            await message.channel.send('No movies found.')

    def select_random_movie(self):
        # Count the number of movies in the collection
        movie_count = self.db.movies.count_documents({})

        if movie_count == 0:
            return "No movies found."

        # Generate a random index for the size of the list
        random_index = random.randint(0, movie_count - 1)

        # Fetch a random movie document
        random_movie = self.db.movies.find().limit(1).skip(random_index).next()

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

    def movie_exists(self, movie_name):
        # Perform a case-insensitive search for the movie name
        result = self.db.movies.find_one({'name': {'$regex': f'^{movie_name}$', '$options': 'i'}})
        return result is not None

    #add the streaming services when inserting into the movie list to save api calls
    #to improve response time and performance at the reduction of timely accuracy
    def insert_movie(self, movie_name):
        try:
            # Capitalize the movie name while excluding certain words
            capitalized_name = capitalize_movie_name(movie_name)
            existing_movie = self.db.movies.find_one({'name': capitalized_name})

            if existing_movie:
                return (capitalized_name, "already exists. Try another movie.")
            # Search for the movie using the TMDb API
            tmdb_search_url = f'https://api.themoviedb.org/3/search/movie?api_key={tmdb.api_key}&query={capitalized_name}'
            response = requests.get(tmdb_search_url)

            if response.status_code == 200:
                movie_data = response.json()
                # Check if we can access results/results exist
                if movie_data['results']:
                    result = movie_data['results'][0]

                    # Extract relevant information
                    movie_title = result['title']
                    release_year = result['release_date'][:4]  # Get the first 4 characters for the year
                    rating = result['vote_average']  # Include the rating

                    # Use the movie's TMDB ID to fetch external IDs, including "where to watch" data
                    tmdb_id = result['id']

                    # services are provided by JustWatch
                    where_to_watch_services = self.get_where_to_watch_services(tmdb_id)

                    # Insert the movie into MongoDB with streaming service names, rating, and US streaming services
                    self.db.movies.insert_one({
                        'name': capitalized_name,
                        'title': movie_title,  # Include the title
                        'release_year': release_year,  # Include the release year
                        'where_to_watch_services': where_to_watch_services,  # Store streaming service names as a list
                        'rating': rating,  # Include the rating
                    })
                else:
                    # (Implied) movie not found in TMDb
                    self.db.movies.insert_one({'name': capitalized_name})  # Use capitalized name here
            return capitalized_name
        except DuplicateKeyError:
            return (capitalized_name, "already exists. Try another movie.")

    def get_where_to_watch_services(self, tmdb_id):
        streaming_providers = []
        try:
            tmdb_watch_providers_url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/watch/providers?api_key={tmdb.api_key}'
            response = requests.get(tmdb_watch_providers_url)

            if response.status_code == 200:
                providers_data = response.json()

                # Check if 'US' region data exists in the response
                # Think about making this adjustable in the future
                #
                if 'results' in providers_data and 'US' in providers_data['results']:
                    us_data = providers_data['results']['US']

                    # Check if 'flatrate' exists in 'US' data
                    if 'flatrate' in us_data:
                        for provider in us_data['flatrate']:
                            provider_name = provider.get('provider_name')
                            if provider_name:
                                streaming_providers.append(provider_name)

            return streaming_providers
        except requests.exceptions.RequestException as e:
            print(f"Error fetching 'where to watch' information: {e}")
            return []

    def list_movies_from_db(self):
        movies = self.db.movies.find().sort('name',
                                            1)  # Sort by 'name' field in ascending order
        movie_list = []

        for movie in movies:
            movie_name = movie['name']
            movie_title = movie.get('title', 'N/A')
            release_year = movie.get('release_year', 'N/A')
            where_to_watch_services = movie.get('where_to_watch_services', [])
            rating = movie.get('rating', 'N/A')

            # Create a dictionary with movie details
            movie_details = {
                'name': movie_name,
                'title': movie_title,
                'release_year': release_year,
                'where_to_watch_services': where_to_watch_services,
                'rating': rating
            }

            movie_list.append(movie_details)

        return movie_list
    def update_movie_in_db(self, movie_name, updated_name):
        self.db.movies.update_one({'name': movie_name}, {'$set': {'name': updated_name}})

    def delete_all_movies_from_db(self):
        result = self.db.movies.delete_many({})
        deleted_count = result.deleted_count
        print(f'{deleted_count} movies deleted.')
        return deleted_count

    def delete_movie_from_db(self, movie_name):
        try:
            # Perform a case-insensitive search for the movie name
            result = self.db.movies.delete_one({'name': {'$regex': f'^{movie_name}$', '$options': 'i'}})

            if result.deleted_count == 0:
                return f'Movie "{movie_name}" not found in the list.'
            else:
                return f'Movie "{movie_name}" deleted from the list.'
        except Exception as e:
            return f'An error occurred while deleting the movie: {str(e)}'

# Intents setup
intents = discord.Intents.default()
intents.message_content = True

async def main():
    async with MyClient(intents=intents) as client:
        await client.start(DISCORD_BOT_TOKEN)

# Run the bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
