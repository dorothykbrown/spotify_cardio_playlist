# Generated by Django 3.2.10 on 2022-03-31 02:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('spotify_app', '0003_song_bpm'),
    ]

    operations = [
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.CharField(max_length=200, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='song',
            name='playlist_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='spotify_app.playlist'),
        ),
    ]
