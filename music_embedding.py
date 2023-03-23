import re
import cohere
import requests
from lxml import html
from bs4 import BeautifulSoup
from unidecode import unidecode


class Album:
    """Album class - Album wrapper

    Attributes:
        title (str): Album title
        songs (list): List of Song objects
    """

    def __init__(self, title, songs):
        self.title = title
        self.songs = songs


class Song:
    """Song class - Song wrapper

    Attributes:
        title (str): Song title
        lyrics (str): Song lyrics
        url (str): Song url
    """

    def __init__(self, title: str, lyrics: str, url: str):
        self.title = title
        self.lyrics = lyrics
        self.url = url

    def set_embedding(self, embedding):
        self.embedding = embedding


class Scraper:
    """Scraper class - Get albums and songs from artist page

    Attributes:
        artist (str): Artist name
        max_albums (int): Max number of albums to get
    """

    def __init__(self, artist, max_albums=100):
        self.artist = artist
        self.max_albums = max_albums
        self.main_url = "https://www.letras.mus.br"
        self.clean_artist = artist.lower().replace(" ", "-")
        self.url = self.main_url + "/" + self.clean_artist + "/discografia"

    def make_request(self, url):
        """Make request with the request module and treat errors"""

        headers = {
            "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
            "sec-ch-ua-mobile": "?0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
        }

        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            print(f"Error - {e.args}")
            return None

        if response.status_code != 200:
            return None

        return response

    def get_albums(self):
        """Get all albums from artist page"""

        response = self.make_request(self.url)
        if response is None:
            return None

        soup = BeautifulSoup(response.text, "lxml")
        albums_tags = soup.find_all("div", class_="album-item g-sp")

        albums = []
        for album_tag in albums_tags:
            album_title = album_tag.find("h1").text.strip()
            info_type = album_tag.find("span", class_="header-info-type").text

            if "Álbum" not in info_type:
                continue

            print(album_title)

            songs_tags = album_tag.find_all("a", class_="bt-play-song")

            songs = []
            for song_tag in songs_tags:
                url = self.main_url + song_tag.get("href")
                response = self.make_request(url)
                if response is None:
                    continue

                tree = html.fromstring(response.content)
                song_title = tree.xpath("//div[@class='cnt-head_title']/text()")

                try:
                    lyrics = tree.xpath('//div[@class="cnt-letra"]//text()')
                    lyrics = "\n".join(lyrics)

                    if "Ainda nÃ£o temos a letra desta mÃºsica." in lyrics:
                        raise Exception("No lyrics")
                except Exception as e:
                    print(f"Couldn't get lyrics {url}")
                    continue

                songs.append(Song(song_title, lyrics, url))

            albums.append(Album(album_title, songs))

            if len(albums) >= self.max_albums:
                break

        return albums


def get_embeddings(albums):
    """Get embeddings from songs"""
    co = cohere.Client("")
    texts = [song.lyrics for album in albums for song in album.songs]
    response = co.embed(model="large", texts=texts)

    for album in albums:
        for song in album.songs:
            song.embedding = response.embeddings.pop(0)

    return albums


if __name__ == "__main__":
    artist = "coldplay"
    scraper = Scraper(artist, max_albums=1)
    albums = scraper.get_albums()

    albums = get_embeddings(albums)
    print(albums[0].songs[0].embedding)
