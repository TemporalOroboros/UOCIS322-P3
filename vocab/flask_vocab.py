"""
Flask web site with vocabulary matching game
(identify vocabulary words that can be made
from a scrambled string)
"""

import flask
import logging
import random
import string
from os import urandom

# Our modules
from src.letterbag import LetterBag
from src.vocab import Vocab
from src.jumble import jumbled
import src.config as config


###
# Globals
###
app = flask.Flask(__name__)

CONFIG = config.configuration()
app.secret_key = urandom(24)	# Should allow using session variables

#
# One shared 'Vocab' object, read-only after initialization,
# shared by all threads and instances.	Otherwise we would have to
# store it in the browser and transmit it on each request/response cycle,
# or else read it from the file on each request/responce cycle,
# neither of which would be suitable for responding keystroke by keystroke.

WORDS = Vocab(CONFIG.VOCAB)

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
	"""The main page of the application"""
	flask.g.vocab = WORDS.as_list()
	
	flask.session["target_count"] = min(
		len(flask.g.vocab), CONFIG.SUCCESS_AT_COUNT)
	flask.session["jumble"] = jumbled(
		flask.g.vocab, flask.session["target_count"])
	flask.session["matches"] = []
	flask.session["success"] = False
	app.logger.debug("Session variables have been set")

	assert flask.session["matches"] == [], "Matches found on initial load"
	assert flask.session["target_count"] >= 0, "Target count is below or equal to zero"
	assert not flask.session["success"], "Success has been registered at init"
	app.logger.debug("At least one seems to be set correctly")
	
	return flask.render_template('vocab.html')


@app.route("/success")
def success():
	if not flask.session["success"]:
		flask.abort(403)
	return flask.render_template('success.html'), 200

###############
# AJAX request handlers
#	These return JSON, rather than rendering pages.
###############

@app.route("/_check")
def check():
	"""
	Checks whether a text string a user has
	entered is a valid word for this game.
	"""
	app.logger.debug("Entering check")

	# The data we need, from the from and cookies.
	text = flask.request.args.get("text", type=str)
	jumble = flask.session["jumble"]
	matches = flask.session.get("matches", []) # Default to an empty list

	# Failure checks:
	app.logger.debug("Checking text string: {}".format(text))
	if text in matches:
		return flask.jsonify(result={"stat": "failure", "message": "duplicate"}), 200
	if not WORDS.has(text):
		return flask.jsonify(result={"stat": "failure", "message": "no_match"}), 200
	if not LetterBag(jumble).contains(text):
		return flask.jsonify(result={"stat": "failure", "message": "anagram"}), 200
	
	# Success state:
	matches.append(text)
	flask.session["matches"] = matches
	if len(matches) < flask.session["target_count"]:
		return flask.jsonify(result={"stat": "success", "text": text}), 200
	
	flask.session["success"] = True
	return flask.jsonify(result={"stat": "success", "text": text, "redirect": flask.url_for("success")}), 200


#################
# Functions used within the templates
#################

@app.template_filter('to_text')
def format_filt(something):
	"""
	Example of a filter that can be used within
	the Jinja2 code
	"""
	return "{}".format(something)

###################
#	Error handlers
###################

@app.errorhandler(404)
def error_404(e):
	app.logger.warning("++ 404 error: {}".format(e))
	return flask.render_template('404.html'), 404


@app.errorhandler(500)
def error_500(e):
	app.logger.warning("++ 500 error: {}".format(e))
	assert not True  # I want to invoke the debugger
	return flask.render_template('500.html'), 500


@app.errorhandler(403)
def error_403(e):
	app.logger.warning("++ 403 error: {}".format(e))
	return flask.render_template('403.html'), 403


#############

if __name__ == "__main__":
	if CONFIG.DEBUG:
		app.debug = True
		app.logger.setLevel(logging.DEBUG)
		app.logger.info(
			"Opening for global access on port {}".format(CONFIG.PORT))
		app.run(port=CONFIG.PORT, host="0.0.0.0")
