import logging

from app.api.application import create_app


logging.basicConfig(level=logging.INFO)
app = create_app()
