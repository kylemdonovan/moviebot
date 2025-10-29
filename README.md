# 🎬 MovieBot

A Discord bot that helps manage your movie list using MongoDB and TMDB.  
Add, update, delete, and pick random movies — complete with ratings and streaming availability.

---

## 🚀 Features

- Add and store movies in MongoDB  
- Automatically fetch movie details (title, release year, rating, streaming services) from TMDB  
- View your movie list directly in Discord  
- Random movie selector for movie nights  
- Changeable command prefix (default: `!`)  
- Commands for adding, deleting, updating, and rolling dice (just for fun)  

---

## 🧩 Commands

```bash
!setprefix <new_prefix>     # Change the command prefix
!addmovie <movie_name>      # Add a movie to your list
!listmovies                 # Show all stored movies
!updatemovie <old> <new>    # Update a movie’s name
!deletemovie <movie_name>   # Delete a specific movie
!deleteall                  # Delete all movies
!randommovie                # Pick a random movie
!roll <number>              # Roll a dice
!help                       # Show help message

<img width="444" alt="image" src="https://github.com/kylemdonovan/moviebot/assets/97189054/33dd85d6-ac19-4977-8255-67b1a2ce8762">
