from django.db import models

# Create your models here.


class Song(models.Model):
    bpm = models.FloatField
    uri = models.CharField(max_length=200)
