# Generated by Django 3.2.10 on 2022-03-31 02:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spotify_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='name',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='song',
            name='id',
            field=models.CharField(max_length=200, primary_key=True, serialize=False),
        ),
    ]