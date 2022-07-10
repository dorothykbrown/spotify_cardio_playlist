from django.db import models

# Create your models here.


class Song(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    bpm = models.FloatField()
    uri = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    playlist_id = models.ForeignKey(
        "Playlist",
        on_delete=models.SET_NULL,
        null=True
    )


class Playlist(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    created = models.DateTimeField("created", auto_now_add=True)
