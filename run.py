from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        use_reloader=app.config["DEBUG"],
        use_debugger=False,
        allow_unsafe_werkzeug=True,
    )
