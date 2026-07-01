"""Thin entrypoint. All real logic lives in surfweb/, services/, providers/,
and ranking/. This module exists so `gunicorn app:app` and `python app.py`
keep working exactly as before.
"""

import os

from surfweb import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
