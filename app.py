import functools
import os

import dotenv
import requests
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

dotenv.load_dotenv(override=True)

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)

# Configuration for Discord OAuth2
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DISCORD_API_BASE_URL = os.getenv("DISCORD_API_BASE_URL")
DISCORD_OAUTH_AUTHORIZE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"
DISCORD_OAUTH_SCOPES = "identify guilds"
GUILD_ID = os.getenv("GUILD_ID")

# Configuration for directory listing
STATIC_PATH = os.path.join(os.path.dirname(__file__), "static")
FILES_BLACKLIST = {".gitkeep"}


def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "discord_user" not in session:
            return redirect(
                DISCORD_OAUTH_AUTHORIZE_URL
                + "?client_id="
                + CLIENT_ID
                + "&redirect_uri="
                + REDIRECT_URI
                + "&response_type=code&scope="
                + DISCORD_OAUTH_SCOPES
            )
        return f(*args, **kwargs)

    return wrapper


@app.route("/")
@app.route("/<path:path>")
@login_required
def home(path=None):
    def _list_files(parent: str) -> list[str]:
        return [
            f"{file}/" if os.path.isdir(os.path.join(parent, file)) else file
            for file in os.listdir(parent)
            if file not in FILES_BLACKLIST
        ]

    if not path:
        return render_template(
            "index.jinja", path="/", files=_list_files(STATIC_PATH)
        )

    if os.path.basename(path) in FILES_BLACKLIST:
        abort(404)

    full_path = os.path.abspath(os.path.join(STATIC_PATH, path))
    if os.path.commonprefix([STATIC_PATH, full_path]) != STATIC_PATH:
        abort(404)

    if not os.path.exists(full_path):
        abort(404)

    if os.path.isdir(full_path):
        return render_template(
            "index.jinja", path=f"/{path.lstrip('/')}", files=_list_files(full_path)
        )

    return send_from_directory("static", path)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code is None:
        return redirect(url_for("home"))

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": DISCORD_OAUTH_SCOPES,
    }
    response = requests.post(
        url=DISCORD_OAUTH_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code != 200:
        return redirect(url_for("home"))

    response_data = response.json()
    access_token = response_data["access_token"]

    # Fetch user info
    user_info = requests.get(
        url=f"{DISCORD_API_BASE_URL}/users/@me",
        headers={"Authorization": "Bearer " + access_token},
    ).json()

    # Fetch guilds info
    guilds = requests.get(
        f"{DISCORD_API_BASE_URL}/users/@me/guilds",
        headers={"Authorization": "Bearer " + access_token},
    ).json()

    # Check if the user is in the specified guild
    if any(guild["id"] == GUILD_ID for guild in guilds):
        session["discord_user"] = user_info
        return redirect(url_for("home"))
    else:
        return ("You're not allowed to view this website.", 403)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
