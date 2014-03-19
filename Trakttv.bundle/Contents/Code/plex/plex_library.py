from core.logger import Logger
from plex.plex_base import PlexBase
from plex.plex_objects import PlexShow, PlexEpisode, PlexMovie
from plex.plex_matcher import PlexMatcher
from plex.plex_metadata import PlexMetadata
from plex.plex_media_server import PlexMediaServer

log = Logger('plex.plex_library')


class PlexLibrary(PlexBase):
    @classmethod
    def map_item(cls, table, data):
        # Get the key for the item
        parsed_guid, key = PlexMetadata.get_key(data.get('ratingKey'))
        if parsed_guid is None:
            return False

        if key not in table:
            table[key] = []

        # Create object for the data
        data_type = data.get('type')
        if data_type == 'movie':
            item = PlexMovie.create(data, parsed_guid, key)
        elif data_type == 'show':
            item = PlexShow.create(data, parsed_guid, key)
        else:
            log.info('Unknown item "%s" with type "%s"', data.get('ratingKey'), data_type)
            return False

        # Map item into table
        table[key].append(item)
        return True

    @classmethod
    def fetch(cls, types=None, keys=None, cache_id=None):
        if types and isinstance(types, basestring):
            types = [types]

        # Get all sections or filter based on 'types' and 'sections'
        sections = [(type, key) for (type, key, _) in PlexMediaServer.get_sections(types, keys, cache_id=cache_id)]

        movies = {}
        shows = {}

        for type, key in sections:
            if type == 'movie':
                for video in PlexMediaServer.get_videos(key, cache_id=cache_id):
                    cls.map_item(movies, video)

            if type == 'show':
                for directory in PlexMediaServer.get_directories(key, cache_id=cache_id):
                    cls.map_item(shows, directory)

        if len(types) == 1:
            if types[0] == 'movie':
                return movies

            if types[0] == 'show':
                return shows

        return movies, shows

    @classmethod
    def fetch_episodes(cls, key, parent=None, cache_id=None):
        """Fetch the episodes for a show from the Plex library

        :param key: Key of show to fetch episodes for
        :type key: str

        :param cache_id: Cached response identifier
        :type cache_id: str

        :return: Dictionary containing the episodes in this form: {season_num: {episode_num: <PlexEpisode>}}
        :rtype: dict
        """

        result = {}

        container = cls.request('library/metadata/%s/allLeaves' % key, timeout=10, cache_id=cache_id)

        for video in container:
            season, episodes = PlexMatcher.get_identifier(video)

            obj = PlexEpisode.create(video, season, episodes, parent=parent)

            for episode in episodes:
                result[season, episode] = obj

        # Ensure PlexMatcher cache is stored to disk
        PlexMatcher.save()

        return result
