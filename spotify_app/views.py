from django.http import HttpResponse
from .models import Playlist, Song
from django.shortcuts import render

# Create your views here.


def index(request):
    all_playlists = Playlist.objects.order_by('-created')[:10]
    context = {'all_playlists': all_playlists}
    return render(request, 'spotify_app/index.html', context)


def create_playlist(request):
    return HttpResponse("You're at the page for creating a new playlist.")


def playlist(request, playlist_id):
    all_songs = Song.objects.order_by("-bpm")
    all_song_names = [song.name for song in all_songs]
    return HttpResponse(all_song_names)
