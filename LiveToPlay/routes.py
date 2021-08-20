from flask import render_template, session, request, flash, redirect, url_for 
from LiveToPlay.forms import LookUpForm     # for search forms 
from LiveToPlay.models import Tracklist, Track, SpotifyLink
from LiveToPlay import app, db
from TracklistScraper.tracklist import *
import spotipy     # for spotify 
from spotipy.oauth2 import SpotifyOAuth
from SpotifyWebAPI.spotifyAPI import *
import sqlite3   # for database 
from werkzeug.exceptions import abort   # for 404 error
import time

TOKEN_INFO = "token_info"
clientID = '85492417c1244f0283cc2198c85efa5c'
clientSecret = '94185058d5df4575b529425f8a6945f7'
clientScope = "user-library-read,user-read-currently-playing,playlist-modify-public"

# index/root/homepage
@app.route("/")
@app.route("/index")
def index():
	return render_template('index.html', title="Home")

# Spotify login page
@app.route("/login")   
def login():
	sp_oauth = create_spotify_oauth(clientID, clientSecret, clientScope)
	auth_url = sp_oauth.get_authorize_url()
	return redirect(auth_url)     # return the redict URL

# redirect to this page after logging into spotify 
@app.route('/redirect')
def redirectPage():
	sp_oauth = create_spotify_oauth(clientID, clientSecret, clientScope)
	session.clear()
	code = request.args.get('code')
	token_info = sp_oauth.get_access_token(code)
	session[TOKEN_INFO] = token_info  # refresh & access token, and expires
	sp = spotipy.Spotify(auth = token_info['access_token'])   
	flash(f'Logged In To Spotify. User: ' + sp.me()['id'], 'success')
	return redirect(url_for('index', _external=True))

# search page 
@app.route("/search", methods=['GET', 'POST'])
def search():
	# create search form 
	form = LookUpForm()

	# check if valid input 
	if form.validate_on_submit():
		# tries to get spotify Oauth Token 
		try:
			token_info = get_token()   
		except:      # exception raised, if fails prompt user to sign in again
			return redirect(url_for('login', _external=True))   # redirect to log in again

		# display success alert 
		flash(f'Search performed for: {form.url.data}', 'success')
		tracklist = Tracklists(url=form.url.data)   # using url create tracklist object
		
		# get spotipy object, and query spotify 
		sp = spotipy.Spotify(auth = token_info['access_token'])   
		searchResults = searchSpot(sp, tracklist.tracks)
		spotplaylist = createPlaylist(sp, searchResults, tracklist)   # create playlist using tracklist
		if not spotplaylist:
			return render_template('search.html', title="Search", form = form)
		# set session variable (to be passed along to redirect page)
		session['tracklistJSON'] = tracklist.tracklistJSON()
		return redirect(url_for('result'))
	return render_template('search.html', title="Search", form = form)



#
# Dummy data 
#
posts = [
	{
		'author' : 'Jane Doe',
		'title' : 'Post Title 1',
		'content' : 'Jane Doe Post 1',
		'date_posted' : '00/00/00'
	},
	{
		'author' : 'John Smith',
		'title' : 'Post Title 2',
		'content' : 'John Smith Post 2',
		'date_posted' : '11/11/11'
	}

]

# search result page
@app.route("/result")
def result():
	# get tracklist session variable 
	tracklistString = session.get('tracklistJSON', None)

	# check if it exists 
	if tracklistString:
		tracklist = json.loads(tracklistString)
		# remember to remove session variable after displaying information 
		session.pop('tracklistJSON')
		return render_template('result.html', title=tracklist["title"], content=tracklist["content"], 
			posts=posts, tracks=tracklist["tracks"]) # pass in posts variable
	return redirect(url_for('search'))

# Get session token 
# if none exist, need to raise exception
def get_token():
	token_info = session.get(TOKEN_INFO, None)
	if not token_info:
		raise "exception: "
	now = int(time.time())
	is_expired = token_info['expires_at'] - now < 60
	if (is_expired):
		sp_oauth = create_spotify_oauth()
		token_info = sp_oauth.refresh_access_token[token_info['refresh_token']]
	return token_info


