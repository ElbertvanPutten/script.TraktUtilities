# -*- coding: utf-8 -*-
# 

import os
import xbmc,xbmcaddon,xbmcgui
import time, socket
import simplejson as json
import urllib, re

try:
    # Python 3.0 +
    import http.client as httplib
except ImportError:
    # Python 2.7 and earlier
    import httplib

try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha
  
__author__ = "Ralph-Gordon Paul, Adrian Cowan"
__credits__ = ["Ralph-Gordon Paul", "Adrian Cowan", "Justin Nemeth",  "Sean Rudford"]
__license__ = "GPL"
__maintainer__ = "Ralph-Gordon Paul"
__email__ = "ralph-gordon.paul@uni-duesseldorf.de"
__status__ = "Production"

# read settings
__settings__ = xbmcaddon.Addon( "script.TraktUtilities" )
__language__ = __settings__.getLocalizedString

apikey = '48dfcb4813134da82152984e8c4f329bc8b8b46a'
username = __settings__.getSetting("username")
pwd = sha.new(__settings__.getSetting("password")).hexdigest()
debug = __settings__.getSetting( "debug" )

conn = httplib.HTTPConnection('api.trakt.tv')
headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def Debug(msg, force=False):
    if (debug == 'true' or force):
        try:
            print "Trakt Utilities: " + msg
        except UnicodeEncodeError:
            print "Trakt Utilities: " + msg.encode( "utf-8", "ignore" )

def notification( header, message, time=5000, icon=__settings__.getAddonInfo( "icon" ) ):
    xbmc.executebuiltin( "XBMC.Notification(%s,%s,%i,%s)" % ( header, message, time, icon ) )

def checkSettings(daemon=False):
    if username == "":
        if daemon:
            notification("Trakt Utilities", __language__(1106).encode( "utf-8", "ignore" )) # please enter your Username and Password in settings
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1106).encode( "utf-8", "ignore" )) # please enter your Username and Password in settings
        return False
    elif __settings__.getSetting("password") == "":
        if daemon:
            notification("Trakt Utilities", __language__(1107).encode( "utf-8", "ignore" )) # please enter your Password in settings
        else:
            xbmcgui.Dialog().ok("Trakt Utilities", __language__(1107).encode( "utf-8", "ignore" )) # please enter your Password in settings
        return False
    
    return True

# make a httpapi based XBMC db query (get data)
def xbmcHttpapiQuery(query):
    Debug("[httpapi-sql] query: "+query)
    xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus(query), )
    match = re.findall( "<field>((?:[^<]|<(?!/))*)</field>", xml_data,)
    Debug("[httpapi-sql] responce: "+xml_data)
    Debug("[httpapi-sql] matches: "+str(match))
    if len(match) <= 0:
        return None
    return match

# execute a httpapi based XBMC db query (set data)
def xbmcHttpapiExec(query):
    xml_data = xbmc.executehttpapi( "ExecVideoDatabase(%s)" % urllib.quote_plus(query), )
    return xml_data

# make a JSON api request to trakt
# method: http method (GET or POST)
# req: REST request (ie '/user/library/movies/all.json/%%API_KEY%%/%%USERNAME%%')
# args: arguments to be passed by POST JSON (only applicable to POST requests), default:{}
# anon: anonymous (dont send username/password), default:False
def traktJsonRequest(method, req, args={}, anon=False):
    try:
        req = req.replace("%%API_KEY%%",apikey)
        req = req.replace("%%USERNAME%%",username)
        if method == 'POST':
            if not anon:
                args['username'] = username
                args['password'] = pwd
            jdata = json.dumps(args)
            conn.request('POST', req, jdata)
        elif method == 'GET':
            conn.request('GET', req)
        else:
            return None
    except socket.error:
        Debug("traktQuery: can't connect to trakt")
        notification("Trakt Utilities", __language__(1108).encode( "utf-8", "ignore" )) # can't connect to trakt
        return None

    response = conn.getresponse()
    try:
        raw = response.read()
        data = json.loads(raw)
    except json.decode.JSONDecodeError:
        Debug("traktQuery: Bad JSON responce: "+raw)
        notification("Trakt Utilities", __language__(1109).encode( "utf-8", "ignore" ) + ": Bad responce from trakt") # Error
        return None
    
    if 'status' in data:
        if data['status'] == 'failure':
            Debug("traktQuery: Error: " + str(data['error']))
            notification("Trakt Utilities", __language__(1109).encode( "utf-8", "ignore" ) + ": " + str(data['error'])) # Error
            return None
    
    return data
# get movies from trakt server
def getMoviesFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/movies/all.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getMoviesFromTrakt()'")
    return data

# get easy access to movie by imdb_id
def traktMovieListByImdbID(data):
    trakt_movies = {}

    for i in range(0, len(data)):
        trakt_movies[data[i]['imdb_id']] = data[i]
        
    return trakt_movies

# get seen tvshows from trakt server
def getWatchedTVShowsFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/shows/watched.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchedTVShowsFromTrakt()'")
    return data
    
# get tvshow collection from trakt server
def getTVShowCollectionFromTrakt(daemon=False):
    data = traktJsonRequest('POST', '/user/library/shows/collection.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getTVShowCollectionFromTrakt()'")
    return data
    
# get tvshows from XBMC
def getTVShowsFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows','params':{'fields': ['title', 'year', 'imdbnumber', 'playcount']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getTVShowsFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        return result['result']
    except KeyError:
        Debug("getTVShowsFromXBMC: KeyError: result['result']")
        return None
    
# get seasons for a given tvshow from XBMC
def getSeasonsFromXBMC(tvshow):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetSeasons','params':{'tvshowid': tvshow['tvshowid']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getSeasonsFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']
    except KeyError:
        Debug("getSeasonsFromXBMC: KeyError: result['result']")
        return None
    
# get episodes for a given tvshow / season from XBMC
def getEpisodesFromXBMC(tvshow, season):
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes','params':{'tvshowid': tvshow['tvshowid'], 'season': season, 'fields': ['playcount', 'episode']}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)

    # check for error
    try:
        error = result['error']
        Debug("getEpisodesFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error

    try:
        return result['result']
    except KeyError:
        Debug("getEpisodesFromXBMC: KeyError: result['result']")
        return None

# get movies from XBMC
def getMoviesFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies','params':{'fields': ['title', 'year', 'originaltitle', 'imdbnumber', 'playcount', 'lastplayed']}, 'id': 1})

    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getMoviesFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        return result['result']['movies']
        Debug("getMoviesFromXBMC: KeyError: result['result']['movies']")
    except KeyError:
        return None

# sets the playcount of a given movie by imdbid
def setXBMCMoviePlaycount(imdb_id, playcount):

    # httpapi till jsonrpc supports playcount update
    # c09 => IMDB ID
    match = xbmcHttpapiQuery(
    "SELECT movie.idFile FROM movie"+
    " WHERE movie.c09='%(imdb_id)s'" % {'imdb_id':str(imdb_id)})
    
    if match == None:
        #add error message here
        return
    
    result = xbmcHttpapiExec(
    "UPDATE files"+
    " SET playcount=%(playcount)d" % {'playcount':int(playcount)}+
    " WHERE idFile=%(idFile)s" % {'idFile':match[0]})
    
    Debug("xml answer: " + str(result))

# sets the playcount of a given episode by tvdb_id
def setXBMCEpisodePlaycount(tvdb_id, seasonid, episodeid, playcount):
    # httpapi till jsonrpc supports playcount update
    # select tvshow by tvdb_id # c12 => TVDB ID # c00 = title
    match = xbmcHttpapiQuery(
    "SELECT tvshow.idShow, tvshow.c00 FROM tvshow"+
    " WHERE tvshow.c12='%(tvdb_id)s'" % {'tvdb_id':str(tvdb_id)})
    
    if len(match) >= 1:
        Debug("TV Show: " + match[1] + " idShow: " + str(match[0]) + " season: " + str(seasonid) + " episode: " + str(episodeid))

        # select episode table by idShow
        match = xbmcHttpapiQuery(
        "SELECT tvshowlinkepisode.idEpisode FROM tvshowlinkepisode"+
        " WHERE tvshowlinkepisode.idShow=%(idShow)s" % {'idShow':str(match[0])})
        
        for idEpisode in match:
            # get idfile from episode table # c12 = season, c13 = episode
            match2 = xbmcHttpapiQuery(
            "SELECT episode.idFile FROM episode"+
            " WHERE episode.idEpisode=%(idEpisode)d" % {'idEpisode':int(idEpisode)}+
            " AND episode.c12='%(seasonid)s'" % {'seasonid':str(seasonid)}+
            " AND episode.c13='%(episodeid)s'" % {'episodeid':str(episodeid)})
            
            if match2 != None:
                for idFile in match2:
                    Debug("idFile: " + str(idFile) + " setting playcount...")
                    responce = xbmcHttpapiExec(
                    "UPDATE files"+
                    " SET playcount=%(playcount)s" % {'playcount':str(playcount)}+
                    " WHERE idFile=%(idFile)s" % {'idFile':str(idFile)})
                    
                    Debug("xml answer: " + str(responce))
    else:
        Debug("setXBMCEpisodePlaycount: no tv show found for tvdb id: " + str(tvdb_id))
    
# get current video being played from XBMC
def getCurrentPlayingVideoFromXBMC():
    rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoPlaylist.GetItems','params':{}, 'id': 1})
    
    result = xbmc.executeJSONRPC(rpccmd)
    result = json.loads(result)
    
    # check for error
    try:
        error = result['error']
        Debug("getCurrentPlayingVideoFromXBMC: " + str(error))
        return None
    except KeyError:
        pass # no error
    
    try:
        Debug("Current playlist: "+str(result['result']))
        current = result['result']['state']['current']
        typ = result['result']['items'][current]['type']
        if typ in ("movie","episode"):
            return result['result']['items'][current]
        return None
    except KeyError:
        Debug("getCurrentPlayingVideoFromXBMC: KeyError")
        return None

def getMovieIdFromXBMC(imdb_id, title):
    # httpapi till jsonrpc supports selecting a single movie
    # Get id of movie by movies IMDB
    Debug("Searching for movie: "+imdb_id+", "+title)
    
    match = xbmcHttpapiQuery(
    " SELECT idMovie FROM movie"+
    "  WHERE c09='%(imdb_id)s'" % {'imdb_id':imdb_id}+
    " UNION"+
    " SELECT idMovie FROM movie"+
    "  WHERE upper(c00)='%(title)s'" % {'title':title.upper()}+
    " LIMIT 1")
    
    if match == None:
        Debug("getMovieIdFromXBMC: cannot find movie in database")
        return -1
        
    return match[0]
   
# returns list of movies from watchlist
def getWatchlistMoviesFromTrakt():
    data = traktJsonRequest('POST', '/user/watchlist/movies.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchlistMoviesFromTrakt()'")
    return data

# returns list of tv shows from watchlist
def getWatchlistTVShowsFromTrakt():
    data = traktJsonRequest('POST', '/user/watchlist/shows.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchlistTVShowsFromTrakt()'")
    return data

# add an array of movies to the watch-list
def addMoviesToWatchlist(data):
    # This function has not been tested, please test it before using it
    movies = []
    for item in data:
        if "imdb_id" in item:
            movie["imdb_id"] = item["imdb_id"]
        if "tmdb_id" in item:
            movie["tmdb_id"] = item["tmdb_id"]
        if "title" in item:
            movie["title"] = item["title"]
        if "year" in item:
            movie["year"] = item["year"]
        movies.append(movie)
    
    data = traktJsonRequest('POST', '/movie/watchlist/%%API_KEY%%', {"movies":movies})
    if data == None:
        Debug("Error in request from 'addMoviesToWatchlist()'")
    return data

#Set the rating for a movie on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateMovieOnTrakt(imdbid, title, year, rating):
    if not (rating in ("love", "hate")):
        #add error message
        return
    
    Debug("Rating movie:" + rating)
    
    data = traktJsonRequest('POST', '/rate/movie/%%API_KEY%%', {'imdb_id': imdbid, 'title': title, 'year': year, 'rating': rating})
    if data == None:
        Debug("Error in request from 'rateMovieOnTrakt()'")
    return data

#Set the rating for a tv episode on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateEpisodeOnTrakt(tvdbid, title, year, season, episode, rating):
    if not (rating in ("love", "hate")):
        #add error message
        return
    
    Debug("Rating episode:" + rating)
    
    data = traktJsonRequest('POST', '/rate/episode/%%API_KEY%%', {'tvdb_id': tvdbid, 'title': title, 'year': year, 'season': season, 'episode': episode, 'rating': rating})
    if data == None:
        Debug("Error in request from 'rateEpisodeOnTrakt()'")
    return data
    
#Set the rating for a tv show on trakt, rating: "hate" = Weak sauce, "love" = Totaly ninja
def rateShowOnTrakt(tvdbid, title, year, rating):
    if not (rating in ("love", "hate")):
        #add error message
        return
    
    Debug("Rating show:" + rating)
    try:
        jdata = json.dumps({'username': username, 'password': pwd, 'tvdb_id': tvdbid, 'title': title, 'year': year, 'rating': rating})
        conn.request('POST', '/rate/show/' + apikey, jdata)
    except socket.error:
        Debug("rateShowOnTrakt: can't connect to trakt")
        notification("Trakt Utilities", __language__(1108).encode( "utf-8", "ignore" )) # can't connect to trakt
        return None

    response = conn.getresponse()
    data = json.loads(response.read())

    try:
        if data['status'] == 'failure':
            Debug("rateShowOnTrakt: Error: " + str(data['error']))
            notification("Trakt Utilities", __language__(1168).encode( "utf-8", "ignore" ) + ": " + str(data['error'])) # Error submitting rating
            return None
    except TypeError:
        pass
    
    notification("Trakt Utilities", __language__(1167).encode( "utf-8", "ignore" )) # Rating submitted successfully
    
    return data

def getRecommendedMoviesFromTrakt():
    data = traktJsonRequest('POST', '/recommendations/movies/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getRecommendedMoviesFromTrakt()'")
    return data

def getRecommendedTVShowsFromTrakt():
    data = traktJsonRequest('POST', '/recommendations/shows/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getRecommendedTVShowsFromTrakt()'")
    return data

def getTrendingMoviesFromTrakt():
    data = traktJsonRequest('GET', '/movies/trending.json/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getTrendingMoviesFromTrakt()'")
    return data

def getTrendingTVShowsFromTrakt():
    data = traktJsonRequest('GET', '/shows/trending.json/%%API_KEY%%')
    if data == None:
        Debug("Error in request from 'getTrendingTVShowsFromTrakt()'")
    return data

def getFriendsFromTrakt():
    data = traktJsonRequest('POST', '/user/friends.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getFriendsFromTrakt()'")
    return data

def getWatchingFromTraktForUser(name):
    data = traktJsonRequest('POST', '/user/watching.json/%%API_KEY%%/%%USERNAME%%')
    if data == None:
        Debug("Error in request from 'getWatchingFromTraktForUser()'")
    return data

def playMovieById(idMovie):
    # httpapi till jsonrpc supports selecting a single movie
    Debug("Play Movie requested for id: "+str(idMovie))
    if idMovie == -1:
        return # invalid movie id
    else:
        rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoPlaylist.Clear', 'params':{}, 'id': 1})
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
        
        # check for error
        try:
            error = result['error']
            Debug("playMovieById, VideoPlaylist.Clear: " + str(error))
            return None
        except KeyError:
            pass # no error
        
        rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoPlaylist.Add', 'params': {'item': {'movieid': int(idMovie)}}, 'id': 1})
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
            
        # check for error
        try:
            error = result['error']
            Debug("playMovieById, VideoPlaylist.Add: " + str(error))
            return None
        except KeyError:
            pass # no error
        
        rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoPlaylist.Play', 'params': {}, 'id': 1})
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
            
        # check for error
        try:
            error = result['error']
            Debug("playMovieById, VideoPlaylist.Play: " + str(error))
            return None
        except KeyError:
            pass # no error    
        try:
            if result['result']['success']:
                if xbmc.Player().isPlayingVideo():
                    return True
            notification("Trakt Utilities", __language__(1302).encode( "utf-8", "ignore" )) # Unable to play movie
        except KeyError:
            Debug("playMovieById, VideoPlaylist.Play: KeyError")
            return None


"""
ToDo:


"""


"""
for later:
First call "Player.GetActivePlayers" to determine the currently active player (audio, video or picture).
If it is audio or video call Audio/VideoPlaylist.GetItems and read the "current" field to get the position of the
currently playling item in the playlist. The "items" field contains an array of all items in the playlist and "items[current]" is
the currently playing file. You can also tell jsonrpc which fields to return for every item in the playlist and therefore you'll have all the information you need.

"""
