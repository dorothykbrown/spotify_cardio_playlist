import base64
import json
import random
import re
import requests
import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from datetime import date, datetime, timedelta
from exceptions import ResponseException
from secrets import client_id, client_secret, user_id, redirect_uri, scopes
from typing import Optional, Tuple
from urllib.parse import urlencode

# from spotify_app.models import Playlist

# Request authorization
# Create a Playlist; Store it's id
# Allow user to choose what level of cardio exercise they would like and what amount of time they would like to exercise for
# Get songs from user's library who's BPM is greater than 60
# Sort songs by increasing BPM with max increase in BPM between sequential songs being 15 until max desired BPM is reached;
# maintain desired BPM until 5 min before end of session then decrease BPM for cooldown (can use BPM 1/2 difference between desired BPM and resting BPM)
# If BPM difference between sequential songs is greater than 15, get songs similar to those already in list to fill gaps
# Add songs to playlist


cardio_playlists_ids = {
    "pop": "37i9dQZF1DWSJHnPb1f0X3",
    "latin": "37i9dQZF1DWXmQEAjlxGhi",
    "funk": "37i9dQZF1DX946PjwaHnSD",
    "hip hop": "37i9dQZF1DX9oh43oAzkyx",
    "rock": "37i9dQZF1DWZUTt0fNaCPB",
    "retro": "37i9dQZF1DX4osfY3zybD2",
    "soul": "37i9dQZF1DWXUtxBFupUW9",
    "dance": "37i9dQZF1DXdURFimg6Blm",
    "twerk": "37i9dQZF1DX0HRj9P7NxeE",
    "techno": "37i9dQZF1DX36TRAnIL92N",
    "fast pop": "37i9dQZF1DWVhQ5d3I6DeF",
    "trap": "37i9dQZF1DWZqUHC2tviPw",
    "morning": "37i9dQZF1DX8E1Op3UZWf0",
    "90s": "37i9dQZF1DXdMm3yYbD7IO",
    "dancehall": "3Vp3kcErFpuo5i2EZoHFB4",
    "soca": "5lQqaJsg4X6VrMsI0e7tuy",
    "afrobeat": "7MSWTrjufCCftrBNFxaVo3"
}

genre_dict = {
    "pop": "pop",
    "p": "pop",
    "trap": "trap",
    "t": "trap",
    "90s": "90s",
    "retro": "retro",
    "re": "retro",
    "latin": "latin",
    "l": "latin",
    "funk": "funk",
    "f": "funk",
    "rock": "rock",
    "ro": "rock",
    "hip_hop": "hip hop",
    "hh": "hip hop",
    "soul": "soul",
    "s": "soul",
    "dance": "dance",
    "d": "dance",
    "morning": "morning",
    "m": "morning",
    "da": "dancehall",
    "dancehall": "dancehall",
    "a": "afrobeat",
    "afrobeat": "afrobeat",
    "so": "soca",
    "soca": "soca",
}


class Token:
    def __init__(self, access_token, expires_in, refresh_token):
        self.access_token = access_token
        self.created = datetime.now()
        self.expires = self.created + timedelta(seconds=expires_in)
        self.refresh_token = refresh_token

    def update(self, access_token, expires_in):
        self.access_token = access_token
        self.last_modified = datetime.now()
        self.expires = self.last_modified + timedelta(seconds=expires_in)

    def refresh(self):
        token_url = 'https://accounts.spotify.com/api/token'

        request_body = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        encoded_credentials = base64.b64encode(
            client_id.encode() + b':' + client_secret.encode()
        ).decode("utf-8")

        token_headers = {
            "Authorization": "Basic " + encoded_credentials,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_response = requests.post(
            token_url,
            data=request_body,
            headers=token_headers,
        )

        if token_response.get("access_token", None) is None:
            raise Exception("Invalid token response")

        self.update(
            token_response["access_token"],
            token_response["expires_in"]
        )


class MyCardioBeats:

    def __init__(self):
        print("Initializing MyCardioBeats instance...")
        self.user_id = user_id
        self.client_id = client_id
        self.token = None
        self.spotify_client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scopes,
                open_browser=True
            )
        )
        self.cardio_bpm_dict = {  # mapping of desired heart rate zones to corresponding min and max BPMs
            "fat_burn": (120, 141),
            "cardio": (142, 168),
            "peak": (169, 210),
            "f": (120, 141),
            "c": (142, 168),
            "p": (169, 210)
        }
        self.intensity, self.session_length, self.genres = self.get_user_preferences()
        # 80% of the playlist will include top songs; the rest will be recommended
        self.percent_top_songs = 0.8
        self.avg_song_length_min = 3
        self.additional_song_buffer = 10
        self.track_info_dict = {}

        # self.get_authorization_token()  # oauth_token

    def get_authorization_token(self):
        # This function is not currently called
        if self.token is not None:
            if self.token.expires < datetime.now():
                self.token.refresh()

            return self.token.access_token

        print("Getting Spotify authorization token...")

        auth_url = 'https://accounts.spotify.com/authorize'
        token_url = 'https://accounts.spotify.com/api/token'

        state = self.generate_random_string(16)

        auth_headers = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "",
            "state": state,
        }

        auth_response = requests.get(
            auth_url + "?" + urlencode(auth_headers)
        )

        code = auth_response.get("code", None)
        if code is None:
            raise Exception("Invalid authorization response")

        encoded_credentials = base64.b64encode(
            client_id.encode() + b':' + client_secret.encode()
        ).decode("utf-8")

        token_headers = {
            "Authorization": "Basic " + encoded_credentials,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }

        auth_response = requests.post(
            token_url, data=token_data, headers=token_headers)

        auth_response_json = auth_response.json()

        print(auth_response_json)

        access_token = auth_response_json.get("access_token", None)

        if access_token is None:
            raise Exception("Invalid access token returned")

        self.token = Token(
            access_token,
            auth_response_json["expires_in"],
            auth_response_json["refresh_token"]
        )

    def generate_random_string(self, length) -> str:
        # This function is not currently called

        possible_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        new_string = "".join(random.choices(possible_chars, k=length))

        return new_string

    def create_playlist(self) -> Optional[str]:
        """
        Create new playlist and return playlist_id
        https://developer.spotify.com/documentation/web-api/reference/#/operations/create-playlist
        """
        print("Creating playlist...")
        intensity_dict = {
            "fat_burn": "fat_burn",
            "cardio": "cardio",
            "peak": "peak",
            "f": "fat_burn",
            "c": "cardio",
            "p": "peak"
        }

        genres_string = " ".join([genre.title() for genre in self.genres])
        # data = json.dumps(
        #     {
        #         "name": f"""
        #             My {genres_string} Cardio Beats -
        #             {intensity_dict.get(self.intensity, '')} - {date.today()}
        #         """,
        #         "description": "My Cardio Exercise Playlist",
        #         "public": False
        #     }
        # )

        # url = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"
        # print("Access Token: ", self.token.access_token)
        # print("URL: ", url)

        response = self.spotify_client.user_playlist_create(
            self.user_id,
            name=f"""
                My {genres_string} Cardio Beats - 
                {intensity_dict.get(self.intensity, '')} - {date.today()}
            """,
            public=False,
            description=f"My {genres_string} Cardio Exercise Playlist",
        )

        # response = requests.post(
        #     url,
        #     data=data,
        #     headers={
        #         "Content-Type": "application/json",
        #         "Authorization": f"Bearer {self.token.access_token}",
        #     }
        # )

        # if response.status_code != 201:
        #     raise ResponseException(response.status_code)

        # response_json = response.json()
        # playlist_id = response_json["id"]
        # Playlist.objects.create(
        #     id=playlist_id,
        #     name=playlist_name,
        # )

        playlist_id = response.get("id", None)
        if playlist_id is None:
            raise Exception("Error occurred while creating playlist")

        return playlist_id

    def get_user_preferences(self) -> Tuple[str, int]:
        """
        Get user preferences for cardio intensity and length of exercise session
        Returns a tuple of cardio intensity, string and session length, int
        Intensity Options:
            - Fat Burn: 120 - 141 BPM
            - Cardio: 142 - 168 BPM
            - Peak: 169+
        Genre Options:
            - Pop (p)
            - Trap (t)
            - 90s (90s)
            - Retro (re)
            - Latin (l)
            - Funk (f)
            - Rock (ro)
            - Hip Hop (hh)
            - Soul (s)
            - Dance (d)
            - Morning (m)
            - Dancehall (da)
            - Afrobeat (a)
            - Soca (so)
        """

        print("Getting user exercise preferences...")

        intensity = input(
            "Enter your desired level of exercise intensity. "
            "Select from the following: \n - fat_burn (f) \n - cardio (c) \n - peak (p)\n"
        )
        allowable_intensities = ["fat_burn", "f", "cardio", "c", "peak", "p"]
        while intensity not in allowable_intensities:
            intensity = input(
                "Desired level of exercise intensity is not currently supported. "
                "Please select from the following: \n - fat_burn (f) \n - cardio (c) \n - peak (p)\n"
            )

        session_length = input("Enter your session length in minutes:\t")
        while int(session_length) < 5:
            session_length = input(
                "Please enter a minimum session length of 5 minutes:\t")

        genres_input = input(
            "Enter your preferred genres. "
            "Select from the following: \n - pop (p)\n - trap (t)\n - 90s\n - retro (re)\n - latin (l)\n - funk (f)\n"
            " - rock (ro)\n - hip hop (hh)\n - soul (s)\n - dance (d)\n - morning (m)\n - dancehall (da)\n"
            " - afrobeat (a)\n - soca (so)\n"
        )
        allowable_genres = [
            "pop",
            "p",
            "trap",
            "t",
            "90s",
            "retro",
            "re",
            "latin",
            "l",
            "funk",
            "f",
            "rock",
            "ro",
            "hip_hop",
            "hh",
            "soul",
            "s",
            "dance",
            "d",
            "morning",
            "m",
            "da",
            "dancehall",
            "a",
            "afrobeat",
            "so",
            "soca",
        ]
        pattern = ',|, +| +'
        genres = re.split(pattern, genres_input)
        unknown_genres = [
            genre
            for genre in genres
            if (genre is not "" and genre not in allowable_genres)
        ]
        while len(unknown_genres) > 0:
            print("The following genres are unknown: ", unknown_genres)
            genres_input = input(
                "Enter your preferred genres. f"
                "Select from the following: \n - pop (p)\n - trap (t)\n - 90s\n - retro (re)\n - latin (l)\n"
                " - funk (f)\n - rock (ro)\n - hip hop (hh)\n - soul (s)\n - dance (d)\n - morning (m)\n"
                " - dancehall (da)\n - afrobeat (a)\n - soca (so)\n"
            )
            genres = re.split(pattern, genres_input)
            unknown_genres = [
                genre
                for genre in genres
                if genre not in allowable_genres
            ]

        return (intensity, int(session_length), [genre_dict.get(genre) for genre in genres])

    def get_users_top_songs(self):
        # This function is not currently called
        """
        Gets user's top tracks and populates self.track_bpm_dict with track id and uris
        https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-top-artists-and-tracks
        """

        print("Getting user's top songs...")

        url = f"https://api.spotify.com/v1/me/top/tracks"

        limit = 20

        if (
            self.session_length * self.percent_top_songs
            > (limit + self.additional_song_buffer) * self.avg_song_length_min
        ):
            limit = int(
                self.session_length * self.percent_top_songs /
                self.avg_song_length_min - self.additional_song_buffer
            )

        print("Token: ", self.token.access_token)

        response = requests.get(
            url=url,
            params={
                "limit": limit,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token.access_token}",
            }
        )

        response_json = response.json()
        tracks = response_json.get("items")

        if tracks is not None:
            for track in tracks:
                self.track_info_dict[track["id"]] = {
                    "uri": track["uri"],
                    "duration": track["duration_ms"]
                }

    def get_genre_playlist_songs(self):
        """
        Gets cardio songs from users preferred genres and populates self.track_bpm_dict with track id and uris
        https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-top-artists-and-tracks
        """

        print("Getting songs from preferred genres...")
        for genre in self.genres:
            playlist_id = cardio_playlists_ids.get(genre)

            # url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

            # limit = 20

            playlist_track_results = self.spotify_client.playlist_tracks(
                playlist_id,
                fields="items"
            )

            # response = requests.get(
            #     url=url,
            #     params={
            #         "limit": limit,
            #     },
            #     headers={
            #         "Content-Type": "application/json",
            #         "Authorization": f"Bearer {self.token.access_token}",
            #     }
            # )

            # response_json = response.json()
            track_items = playlist_track_results.get("items")

            if track_items is not None:
                for item in track_items:
                    track = item["track"]
                    self.track_info_dict[track["id"]] = {
                        "uri": track["uri"],
                        "duration": track["duration_ms"]
                    }

    def get_song_recommendations(self):
        # This function is not currently called
        """
        Get user's recommended tracks using top artists as seeds and populates self.track_bpm_dict with track id and uris
        https://developer.spotify.com/console/get-recommendations/
        https://developer.spotify.com/documentation/web-api/reference/#/operations/get-users-top-artists-and-tracks
        """

        print("Getting song recommendations...")

        top_artists_url = f"https://api.spotify.com/v1/users/{self.user_id}/top/artists"
        limit = 20

        if (
            self.session_length * (1 - self.percent_top_songs)
            > (limit + self.additional_song_buffer) * self.avg_song_length_min
        ):
            limit = int(
                (self.session_length * (1 - self.percent_top_songs) /
                 self.avg_song_length_min)
                - self.additional_song_buffer
            )

        top_artists_response = requests.get(
            url=top_artists_url,
            params={
                "limit": limit,
                "time_range": "medium_term"
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token.access_token}",
            }
        )

        artists_response_json = top_artists_response.json()
        artists = artists_response_json.get("items")

        seed_track_ids = [
            track_id
            for track_id in self.track_info_dict.keys()
        ]

        if artists is not None:
            seed_artist_ids = [
                artist["id"]
                for artist in artists
            ]
            seed_genres = [
                genre
                for artist in artists
                for genre in artist["genres"]
            ]

            recommendations_url = "https://api.spotify.com/v1/recommendations"
            recommendations_response = requests.get(
                url=recommendations_url,
                data={
                    "seed_artists": seed_artist_ids,
                    "seed_genres": seed_genres,
                    "seed_tracks": seed_track_ids,
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token.access_token}",
                }
            )

            recommendations_response_json = recommendations_response.json()

            tracks = recommendations_response_json.get("tracks")
            for track in tracks:
                self.track_info_dict[track["id"]] = {
                    "uri": track["uri"],
                    "duration": track["duration_ms"]
                }

    def get_track_bpm(self, track_id) -> Optional[str]:
        """https://developer.spotify.com/documentation/web-api/reference/#/operations/get-audio-analysis"""

        print("Getting track bpms")

        # url = f"https://api.spotify.com/v1/audio-analysis/{track_id}"

        # response = requests.get(
        #     url=url,
        #     headers={
        #         "Accept": "application/json",
        #         "Content-Type": "application/json",
        #         "Authorization": f"Bearer {self.token.access_token}",
        #     }
        # )

        # response_json = response.json()

        track_results = self.spotify_client.audio_analysis(track_id)
        track = track_results.get("track", None)
        if track is not None:
            return track["tempo"]

        return None

    def add_songs_to_playlist(self):
        """
        Create list of songs sorted by BPM, create playlist and add songs to playlist
        """
        print("Populating playlist...")

        # populate self.track_bpm_dict
        # self.get_users_top_songs()
        # self.get_song_recommendations()

        self.get_genre_playlist_songs()

        # populate self.track_info_dict with bpms
        print("Populating self.track_info_dict with bpms...")
        for track_id in self.track_info_dict.keys():
            if self.get_track_bpm(track_id) is None:
                del self.track_info_dict[track_id]
                print(f"Deleted track_id {track_id} from self.track_info_dict")
            else:
                self.track_info_dict[track_id]["bpm"] = self.get_track_bpm(
                    track_id
                )

        min_desired_bpm, max_desired_bpm = self.cardio_bpm_dict[self.intensity]

        resting_heartrate_bpm = 75
        total_tracks_duration_ms = 0

        tracks = [
            track
            for track in self.track_info_dict.values()
            if resting_heartrate_bpm < track["bpm"] < max_desired_bpm
        ]

        milliseconds_per_minute = 60000

        print("Total num tracks retrieved: ", len(self.track_info_dict))
        print("Total tracks time (min): ", sum(
            [track["duration"] for track in self.track_info_dict.values()]
        ) / milliseconds_per_minute
        )
        print("Total number of songs with required bpm: ", len(tracks))
        print("Total tracks time (min): ", sum(
            [track["duration"] for track in tracks]
        ) / milliseconds_per_minute
        )

        def track_bpm(track):
            return track["bpm"]

        tracks.sort(key=track_bpm)

        warmup_bpm_1 = resting_heartrate_bpm + \
            (min_desired_bpm - resting_heartrate_bpm) / 3
        warmup_bpm_2 = min_desired_bpm - \
            (min_desired_bpm - resting_heartrate_bpm) / 3

        # sort tracks by ascending and descending bpm
        sorted_tracks = []

        print("Adding warmup tracks to track list...")
        for index, track in enumerate(tracks):
            if (warmup_bpm_1 - 10) < track["bpm"] < (warmup_bpm_1 + 10):
                track = tracks.pop(index)
                # max_track_bpm = track["bpm"]
                sorted_tracks.append(track["uri"])
                total_tracks_duration_ms += track["duration"]
                break

        for index, track in enumerate(tracks):
            if (warmup_bpm_2 - 10) < track["bpm"] < (warmup_bpm_2 + 10):
                track = tracks.pop(index)
                # max_track_bpm = track["bpm"]
                sorted_tracks.append(track["uri"])
                total_tracks_duration_ms += track["duration"]
                break

        print("Adding songs at desired cardio intensity to track list...")
        while (
            total_tracks_duration_ms < (
                self.session_length - 2 * self.avg_song_length_min
            ) * milliseconds_per_minute
        ):
            # num_songs_to_max_desired_bpm = 2
            # while max_desired_bpm - max_track_bpm / num_songs_to_max_desired_bpm > 20:
            #     num_songs_to_max_desired_bpm += 1

            # bpm_delta = max_desired_bpm - max_track_bpm / num_songs_to_max_desired_bpm

            for index, track in enumerate(tracks):
                # if (bpm_delta - 10) < track["bpm"] < (bpm_delta + 10):
                if (max_desired_bpm - 20) < track["bpm"] < max_desired_bpm:
                    track = tracks.pop(index)
                    # max_track_bpm = track["bpm"]
                    sorted_tracks.append(track["uri"])
                    total_tracks_duration_ms += track["duration"]

            break

        print("Adding cooldown tracks to track list...")
        for index, track in enumerate(tracks):
            if (warmup_bpm_2 - 10) < track["bpm"] < (warmup_bpm_2 + 10):
                track = tracks.pop(index)
                sorted_tracks.append(track["uri"])
                total_tracks_duration_ms += track["duration"]
                break

        for index, track in enumerate(tracks):
            if (warmup_bpm_1 - 10) < track["bpm"] < (warmup_bpm_1 + 10):
                track = tracks.pop(index)
                sorted_tracks.append(track["uri"])
                total_tracks_duration_ms += track["duration"]
                break

        # create playlist
        playlist_id = self.create_playlist()

        # request_data = json.dumps({"uris": sorted_tracks})

        # add tracks to playlist
        print("Adding tracks to playlist...")
        if playlist_id is not None:

            self.spotify_client.playlist_add_items(
                playlist_id,
                sorted_tracks
            )
            # add_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

            # add_tracks_response = requests.post(
            #     add_tracks_url,
            #     data=request_data,
            #     headers={
            #         "Content-Type": "application/json",
            #         "Authorization": f"Bearer {self.token.access_token}",
            #     }
            # )

            # if add_tracks_response.status_code != 201:
            #     raise ResponseException(add_tracks_response.status_code)

            print("All tracks have been successfully added to playlist!")
            # add_tracks_response_json = add_tracks_response.json()
            # return add_tracks_response_json


if __name__ == '__main__':
    mcb = MyCardioBeats()
    mcb.add_songs_to_playlist()
    # print(mcb.generate_random_string(10))
