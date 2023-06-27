from discord.ext import commands


class MovieList(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add', help='Add a movie to the list.')
    async def add_movie(self, ctx, movie: str):
        collection.insert_one({"title": movie})
        await ctx.send(f"{movie} added to the list.")

    @commands.command(name='remove', help='Remove a movie from the list.')
    async def remove_movie(self, ctx, movie: str):
        collection.delete_one({"title": movie})
        await ctx.send(f"{movie} removed from the list.")

    @commands.command(name='list', help='List all movies in the database.')
    async def list_movies(self, ctx):
        movies = ""
        for movie in collection.find():
            movies += f"- {movie['title']}\n"
        if not movies:
            await ctx.send("There are no movies in the list.")
        else:
            await ctx.send(movies)


def setup(bot):
    bot.add_cog(MovieList(bot))