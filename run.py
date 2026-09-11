import os
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder="frontend", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    # If the exact file exists in frontend, serve it
    if os.path.exists(os.path.join("frontend", path)):
        return send_from_directory("frontend", path)
    # If path.html exists (e.g. /timetable -> frontend/timetable.html), serve it
    html_path = f"{path}.html"
    if os.path.exists(os.path.join("frontend", html_path)):
        return send_from_directory("frontend", html_path)
    # Fallback to index
    return send_from_directory("frontend", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"UI Prototype server running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)