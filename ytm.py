import os
import youtube_dl
import yt_dlp
import json
import pickle
import re
import pydub

import pytube
import google_auth_oauthlib.flow
import googleapiclient.errors

from googleapiclient.discovery import build

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

config = json.load(open(os.environ["proj_dir"] + "config.json"))


class YTModule:

    def __init__(self, yt_api_client: bool = True, reauth: bool = False, auth_by_user: bool = False):
        """ A class for interacting with YouTube data and either downloading videos or getting video metadata

        Args:
        reauth (bool) : setting this to true will force the module to reauthenticate with the youtube api rather than search for a pickle (default False)
        auth_by_user (bool) : defines which authentication flow to use
        """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        self.youtube = None

        if not os.path.exists(config["pickled_client"]) or reauth:
            # Get credentials and create an API client
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(
                config['yt_client_secret'], scopes
            )
            if auth_by_user:
                credentials = flow.run_local_server()
                self.youtube = build(
                    api_service_name, api_version, credentials=credentials)
            else:
                self.youtube: googleapiclient.discovery.Resource = build(
                    api_service_name, api_version, developerKey=config["youtube_access_key"]
                )
            with open(config["pickled_client"], "wb") as f:
                pickle.dump(self.youtube, f)
        else:
            with open(config["pickled_client"], "rb") as f:
                self.youtube = pickle.load(f)

    def construct_video_url(self, video_id):
        """
        Constructs a video url from a video id
        """
        return f"https://www.youtube.com/watch?v={video_id}"

    def search_videos_by_query(self, query, top=25, published_after=None):
        """
        Searches for videos by query and returns a list of video ids

        Warning: YouTube Data API limits search requests to 50 results and thus this function will paginate to acquire the specified number of results
        Args:
            query (str): the query to search for
            top (int): the number of results to return
            published_after (str): the date to search after in the format YYYY-MM-DDTHH:MM:SSZ
        """

        request = self.youtube.search().list(
            part="snippet", type="video", maxResults=top, q=query, publishedAfter=published_after
        )

        response = request.execute()
        videos = [item["id"]["videoId"] for item in response["items"]]
        try:

            next_page_token = response["nextPageToken"]

            for i in range(50, top, 50):
                print("Getting results from: " +
                      str(i) + " of " + str(top))
                
                request = self.youtube.search().list(
                    part="snippet", type="video", maxResults=50, q=query, pageToken=next_page_token
                )

                response = request.execute()

                next_page_token = response["nextPageToken"]
                videos.extend([i["id"]["videoId"] for i in response["items"]])

        except KeyError:
            print("No more pages")

        return videos

    def search_channels_by_query(self, query, top=25):
        """
        Searches for channels by query and returns a list of channel ids
        
        Warning: YouTube Data API limits search requests to 50 results and thus this function will paginate to acquire the specified number of results

        Args:
            query (str): the query to search for
            top (int): the number of results to return
        """
        request = self.youtube.search().list(
            part="snippet", type="channel", maxResults=top, q=query
        )
        results = request.execute()

        return [item["snippet"]["channelId"] for item in results["items"]]

    def get_channel_videos(self, channel_id, top=25):
        """
        Gets a list of videos from a channel
        Args:
            channel_id (str): the channel id
            top (int): the number of results to return
        """
        request = self.youtube.search().list(
            part="snippet", type="video", maxResults=top, channelId=channel_id, order="date"
        )

        response = request.execute()

        video_list = [item["id"]["videoId"] for item in response["items"]]
        print(video_list)
        try:
            while len(video_list) < top:
                request = self.youtube.search().list(
                    part="snippet", type="video", maxResults=top - len(video_list), channelId=channel_id, order="date", pageToken=response["nextPageToken"]
                )

                response = request.execute()

                video_list.extend([item["id"]["videoId"]
                                  for item in response["items"]])
        except KeyError:
            print("No more pages")

        return video_list

    def download_video(self, url, service="yt-dlp", save_path=None):
        """
        Downloads a video from a url and saves it to the specified path.
        The service which is used to download the video can be chosen, as services will sometimes become out of date.
        Args:
            url (str): the url of the video to download
            service (str): the service to use to download the video. Options are "yt-dlp", "youtube-dl" and "pytube"
            save_path (str): the path to save the video to. If None, the video will be saved to the config save_path
        """
        if service == "youtube-dl":
            self._download_video_youtubedl(url, save_path)
        elif service == "pytube":
            self._download_video_pytube(url, save_path)
        elif service == "yt-dlp":
            self._download_video_ytdlp(url, save_path)
        else:
            print("Invalid service. Please choose either youtube-dl or pytube.")

    def _download_video_youtubedl(self, url, save_path):
        youtube_dl.YoutubeDL(
            {"username": config["username"], "password": config["password"]}
        ).download([url])

    def _download_video_ytdlp(self, url, save_path):
        ydl_opts = {
            'format': 'bestaudio',
            # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
            'postprocessors': [{  # Extract audio using ffmpeg
               'key': 'FFmpegExtractAudio',
               'preferredcodec': 'mp3',
            }],
            'keepvideo': False,
            # the location of the ffmpeg binary
            'ffmpeg_location': config['ffmpeg_location'],
            "outtmpl": os.path.join(config['save_path'] if save_path == None else save_path, '%(title)s-%(id)s.%(ext)s')
        }
        yt_dlp.YoutubeDL(ydl_opts).download([url])


    def _download_video_pytube(self, url, save_path):
        try:
            # Create a YouTube object
            yt = pytube.YouTube(url)

            # Extract metadata
            video_title = yt.title
            video_author = yt.author
            video_length = yt.length
            video_views = yt.views
            video_rating = yt.rating
            video_thumbnail_url = yt.thumbnail_url

            # Print metadata
            print("Title:", video_title)
            print("Author:", video_author)
            print("Length:", video_length, "seconds")
            print("Views:", video_views)
            print("Rating:", video_rating)
            print("Thumbnail URL:", video_thumbnail_url)

            print(
                "FINAL PATH: "
                + yt.streams.first().download(
                    output_path=config['save_path'] if save_path == None else save_path
                )
            )

        except Exception as e:
            print("Error:", str(e))

    def construct_video_json(self, id: str) -> dict:
        """
        Will construct a json object from a video id. The json object will contain the following fields:

        video_id, url, title, desc, channel_name, channel_id, duration, views, likes, comments_count, comments, tags, date_published

        Args:
            id (str): the video id
        """
        vid_json = {}

        try:
            response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics", id=id).execute()['items'][0]
        except IndexError:
            print("Video not found")
            print(id)
            return None

        comments = []
        comments_disabled = False

        try:
            for comment in self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=id,
                maxResults=10,
                searchTerms="",
            ).execute()['items']:
                comments.append(
                    comment['snippet']['topLevelComment']['snippet']['textOriginal'])
        except googleapiclient.errors.HttpError as e:
            if e.error_details[0]['reason'] == "commentsDisabled":
                print("Comments disabled")
                comments = ['<<<Comments Disabled>>>']
                comments_disabled = True
            else:
                raise e
        duration = -1
        try:
            hour_min_secs = re.search(
                r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', response['contentDetails']['duration']).groups()
            duration = int(hour_min_secs[0] or 0) * 3600 + int(
                hour_min_secs[1] or 0) * 60 + int(hour_min_secs[2] or 0)
        except AttributeError as e:
            print(e)
            print(id)
        try:
            vid_json['video_id'] = id
            vid_json['url'] = self.construct_video_url(id)
            vid_json['title'] = response['snippet']['title']
            vid_json['desc'] = response['snippet']['description']
            vid_json['channel_name'] = response['snippet']['channelTitle']
            vid_json['channel_id'] = response['snippet']['channelId']
            vid_json['duration'] = duration
            vid_json['views'] = int(response['statistics']['viewCount'])
            if 'likeCount' in response['statistics']:
                vid_json['likes'] = int(response['statistics']['likeCount'])
            else:
                vid_json['likes'] = -1
            if not comments_disabled:
                vid_json['comments_count'] = int(
                    response['statistics']['commentCount'])
            else:
                vid_json['comments_count'] = -1
            vid_json['comments'] = comments
            if 'tags' in response['snippet']:
                vid_json['tags'] = response['snippet']['tags']
            vid_json['date_published'] = response['snippet']['publishedAt']
        except KeyError as e:
            print(e)
            print(id)

        return vid_json

    def get_video_pytube(self, id):
        return pytube.YouTube(url=self.construct_video_url(id))
    
    def get_video_caption(self, id, save_path='./%(title)s-subtitles'):
        ydl_opts = {
            'writeautomaticsub': True,
            'subtitlesformat': 'srt',
            'skip_download': True,
            'outtmpl': save_path,
            'writesubtitles': True
        }
        return yt_dlp.YoutubeDL(ydl_opts).download([self.construct_video_url(id)])
    
    def crop_mp3(self, path: str, length: int):
        audio = pydub.AudioSegment.from_mp3(path)
        audio = audio[:length * 1000]
        audio.export(path.replace('.mp3', 'shortened.mp3'), format="mp3")

if __name__ == "__main__":
    query = "scambaiting"

    yt = YTModule(reauth=True)
    yt.crop_mp3(path='/home/flynn/Downloads/As I Figure.mp3', length=10)                                                                                              