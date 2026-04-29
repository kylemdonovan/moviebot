import discord
from discord.ext import commands
import aiohttp
import random
from tmdbv3api import TMDb
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Import your secrets
from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME, TMDB_API_KEY, DISCORD_BOT_TOKEN

# --- Setup ---
client_db = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
db = client_db[DATABASE_NAME][COLLECTION_NAME]

intents = discord.Intents.default()
intents.message_content = True

def capitalize_movie_name(movie_name):
    excluded = ['the', 'to', 'a', 'of', 'in', 'and']
    words = movie_name.split()
    if not words: return ""
    words[0] = words[0].capitalize()
    return ' '.join([w.capitalize() if w.lower() not in excluded else w.lower() for w in words])

# --- Bot Class ---
class MovieBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.session = None

    async def setup_hook(self):
        # Initialize the persistent web session for API calls
        self.session = aiohttp.ClientSession()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

bot = MovieBot()

# --- Commands ---
@bot.command(name="addmovie")
async def add_movie(ctx, *, movie_name: str):
    """Adds a movie (or multiple separated by *) to the database."""
    names = [n.strip() for n in movie_name.split('*')]
    added = []

    for name in names:
        cap_name = capitalize_movie_name(name)
        if db.movies.find_one({'name': cap_name}):
            await ctx.send(f"⚠️ '{cap_name}' is already in the list.")
            continue

        # TMDb Search using aiohttp (Non-blocking)
        url = f'https://api.themoviedb.org/3/search/movie'
        params = {'api_key': TMDB_API_KEY, 'query': cap_name}
        
        async with bot.session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['results']:
                    res = data['results'][0]
                    movie_doc = {
                        'name': cap_name,
                        'title': res['title'],
                        'release_year': res.get('release_date', '????')[:4],
                        'rating': res.get('vote_average', 0),
                        'tmdb_id': res['id']
                    }
                    db.movies.insert_one(movie_doc)
                    added.append(cap_name)
                else:
                    db.movies.insert_one({'name': cap_name})
                    added.append(cap_name)

    if added:
        await ctx.send(f"✅ Added: {', '.join(added)}")

@bot.command(name="randommovie")
async def random_movie(ctx):
    """Picks a random movie from your collection."""
    count = db.movies.count_documents({})
    if count == 0:
        return await ctx.send("The list is empty!")
    
    movie = db.movies.find().limit(1).skip(random.randint(0, count - 1)).next()
    
    msg = (f"🎬 **Random Pick:** {movie.get('title', movie['name'])}\n"
           f"🗓️ Year: {movie.get('release_year', 'N/A')}\n"
           f"⭐ Rating: {movie.get('rating', 'N/A')}")
    await ctx.send(msg)

@bot.command(name="listmovies")
async def list_movies(ctx):
    """Lists all movies in the DB."""
    movies = db.movies.find().sort('name', 1)
    output = "**Current Movie List:**\n"
    for m in movies:
        output += f"- {m['name']} ({m.get('release_year', 'N/A')})\n"
    
    # Simple chunking for Discord's 2000 char limit
    if len(output) > 2000:
        for x in range(0, len(output), 2000):
            await ctx.send(output[x:x+2000])
    else:
        await ctx.send(output)

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
