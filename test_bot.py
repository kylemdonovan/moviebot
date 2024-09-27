import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from moviebot import MyClient
import discord

class TestMyClient(unittest.TestCase):
    def setUp(self):
        # Create a mock for discord.Intents
        self.mock_intents = MagicMock(spec=discord.Intents)
        self.mock_intents.message_content = True

        # Patch discord.Intents.default to return our mock
        patcher = patch('discord.Intents.default', return_value=self.mock_intents)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Create the client with the mocked intents
        self.client = MyClient(intents=self.mock_intents)
        self.client.db = MagicMock()

    @patch('moviebot.discord.Client.setup_hook')
    @patch('moviebot.aiohttp.ClientSession')
    async def test_setup_hook(self, mock_session, mock_setup_hook):
        await self.client.setup_hook()
        mock_session.assert_called_once()
        self.assertIsNotNone(self.client.session)

    async def test_set_prefix(self):
        message = AsyncMock()
        await self.client.set_prefix(message, "!")
        self.assertEqual(self.client.prefix, "!")
        message.channel.send.assert_called_once_with("Prefix has been set to: !")

    @patch('moviebot.MyClient.insert_movie')
    async def test_add_movie(self, mock_insert_movie):
        message = AsyncMock()
        mock_insert_movie.return_value = "Test Movie"
        await self.client.add_movie(message, "Test Movie")
        mock_insert_movie.assert_called_once_with("Test Movie")
        message.channel.send.assert_called_once_with('Movies added to the list: Test Movie')

    @patch('moviebot.MyClient.list_movies_from_db')
    async def test_list_movies(self, mock_list_movies):
        message = AsyncMock()
        mock_list_movies.return_value = [
            {
                'name': 'Test Movie',
                'title': 'Test Movie Title',
                'release_year': '2023',
                'where_to_watch_services': ['Netflix', 'Hulu'],
                'rating': 8.5
            }
        ]
        await self.client.list_movies(message)
        mock_list_movies.assert_called_once()
        message.channel.send.assert_called_once()

    @patch('moviebot.MyClient.update_movie_in_db')
    async def test_update_movie(self, mock_update_movie):
        message = AsyncMock()
        await self.client.update_movie(message, "Old Movie New Movie")
        mock_update_movie.assert_called_once_with("Old Movie", "New Movie")
        message.channel.send.assert_called_once_with('Movie "Old Movie" updated to "New Movie".')

    @patch('moviebot.MyClient.movie_exists')
    @patch('moviebot.MyClient.delete_movie_from_db')
    async def test_delete_movie(self, mock_delete_movie, mock_movie_exists):
        message = AsyncMock()
        mock_movie_exists.return_value = True
        mock_delete_movie.return_value = 'Movie "Test Movie" deleted from the list.'
        await self.client.delete_movie(message, "Test Movie")
        mock_delete_movie.assert_called_once_with("Test Movie")
        message.channel.send.assert_called_once_with('Movie "Test Movie" deleted from the list.')

    @patch('moviebot.MyClient.delete_all_movies_from_db')
    async def test_delete_all_movies(self, mock_delete_all):
        message = AsyncMock()
        mock_delete_all.return_value = 5
        await self.client.delete_all_movies(message)
        mock_delete_all.assert_called_once()
        message.channel.send.assert_called_once_with('5 movies have been deleted.')

    @patch('moviebot.random.randint')
    async def test_roll_dice(self, mock_randint):
        message = AsyncMock()
        mock_randint.return_value = 4
        await self.client.roll_dice(message, "6")
        mock_randint.assert_called_once_with(1, 6)
        message.channel.send.assert_called_once_with("You rolled a 6-sided dice and got: 4")

    @patch('moviebot.MyClient.select_random_movie')
    async def test_random_movie(self, mock_select_random):
        message = AsyncMock()
        mock_select_random.return_value = "Random Movie Details"
        await self.client.random_movie(message)
        mock_select_random.assert_called_once()
        message.channel.send.assert_called_once_with("Random Movie Details")

if __name__ == '__main__':
    unittest.main()
