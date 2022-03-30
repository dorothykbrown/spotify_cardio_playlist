import requests
from datetime import date
from secrets import client_id, client_secret, oauth_token, user_id, scopes, redirect_uri
from typing import Optional, Tuple
from exceptions import ResponseException
import base64
from urllib.parse import urlencode
import json

# Request authorization
# Create a Playlist; Store it's id
# Allow user to choose what level of cardio exercise they would like and what amount of time they would like to exercise for
# Get songs from user's library who's BPM is greater than 60
# Sort songs by increasing BPM with max increase in BPM between sequential songs being 15 until max desired BPM is reached;
# maintain desired BPM until 5 min before end of session then decrease BPM for cooldown (can use BPM 1/2 difference between desired BPM and resting BPM)
# If BPM difference between sequential songs is greater than 15, get songs similar to those already in list to fill gaps
# Add songs to playlist


class MyCardioBeats:

    def __init__(self):
        print("Initializing MyCardioBeats instance...")
        self.user_id = user_id
        self.client_id = client_id
        self.token = oauth_token  # self.get_authorization_token()
        self.cardio_bpm_dict = {  # mapping of desired heart rate zones to corresponding min and max BPMs
            "fat_burn": (120, 141),
            "cardio": (142, 168),
            "peak": (169, 210),
            "f": (120, 141),
            "c": (142, 168),
            "p": (169, 210)
        }
        self.intensity, self.session_length = self.get_user_preferences()
        # 80% of the playlist will include top songs; the rest will be recommended
        self.percent_top_songs = 0.8
        self.avg_song_length_min = 3
        self.additional_song_buffer = 10
        self.track_info_dict = {}

    def get_authorization_token(self):
        print("Getting Spotify authorization token...")
        auth_url = 'https://accounts.spotify.com/api/token'
        client_id_and_secret = client_id + ':' + client_secret
        client_id_and_secret_bytes = client_id_and_secret.encode('ascii')

        provider_url = "https://accounts.spotify.com/authorize"

        auth_response = requests.post(
            url=auth_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
            },
            headers={
                'Authorization': f'Basic {base64.b64encode(client_id_and_secret_bytes)}'
            },
        )

        params = urlencode({
            'client_id': client_id,
            'scope': ["playlist-modify-private", "playlist-modify-public", "user-top-read"],
            'redirect_uri': redirect_uri,
            'response_type': 'code'
        })

        url = provider_url + '?' + params

        auth_response_json = auth_response.json()

        return auth_response_json["access_token"]

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
        data = json.dumps(
            {
                "name": f"My Cardio Beats - {intensity_dict.get(self.intensity, '')} - {date.today()}",
                "description": "My Cardio Exercise Playlist",
                "public": False
            }
        )

        url = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"
        print("Token: ", self.token)
        print("URL: ", url)
        response = requests.post(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        )

        if response.status_code != 201:
            raise ResponseException(response.status_code)

        response_json = response.json()

        return response_json["id"]

    def get_user_preferences(self) -> Tuple[str, int]:
        """
        Get user preferences for cardio intensity and length of exercise session
        Returns a tuple of cardio intensity, string and session length, int
        Intensity Options: 
            - Fat Burn: 120 - 141 BPM
            - Cardio: 142 - 168 BPM
            - Peak: 169+
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

        return (intensity, int(session_length))

    def get_users_top_songs(self):
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

        print("Token: ", self.token)

        response = requests.get(
            url=url,
            params={
                "limit": limit,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
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

    def get_song_recommendations(self):
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
                "Authorization": f"Bearer {self.token}",
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
                    "Authorization": f"Bearer {self.token}",
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

        url = f"https://api.spotify.com/v1/audio-analysis/{track_id}"

        response = requests.get(
            url=url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        )

        response_json = response.json()
        track = response_json.get("track")
        if track is not None:
            return track["tempo"]

        return None

    def add_songs_to_playlist(self):
        """
        Create list of songs sorted by BPM, create playlist and add songs to playlist
        """
        print("Populating playlist...")

        # populate self.track_bpm_dict
        self.get_users_top_songs()
        self.get_song_recommendations()

        # populate self.track_info_dict with bpms
        print("Populating self.track_info_dict with bpms...")
        for track_id in self.track_info_dict.keys():
            if self.get_track_bpm(track_id) is None:
                del self.track_info_dict[track_id]
                print(f"Deleted track_id {track_id} from self.track_info_dict")
            else:
                self.track_info_dict[track_id]["bpm"] = self.get_track_bpm(
                    track_id)

        min_desired_bpm, max_desired_bpm = self.cardio_bpm_dict[self.intensity]

        resting_heartrate_bpm = 75
        total_tracks_duration_ms = 0

        tracks = [
            track
            for track in self.track_info_dict.values()
            if resting_heartrate_bpm < track["bpm"] < max_desired_bpm
        ]

        def track_bpm(track):
            return track["bpm"]

        tracks.sort(key=track_bpm)

        max_track_bpm = 0
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

        milliseconds_per_minute = 60_000

        print("Adding songs at desired cardio intensity to track list...")
        while (
            total_tracks_duration_ms < self.session_length *
                milliseconds_per_minute - 2 * self.avg_song_length_min
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

        request_data = json.dumps({"uris": sorted_tracks})

        # add tracks to playlist
        print("Adding tracks to playlist...")
        if playlist_id is not None:
            add_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"

            add_tracks_response = requests.post(
                add_tracks_url,
                data=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                }
            )

            if add_tracks_response.status_code != 201:
                raise ResponseException(add_tracks_response.status_code)

            print("All tracks have been successfully added to playlist!")
            add_tracks_response_json = add_tracks_response.json()
            return add_tracks_response_json


if __name__ == '__main__':
    mcb = MyCardioBeats()
    mcb.add_songs_to_playlist()
