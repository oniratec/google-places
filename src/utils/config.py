import os
from pathlib import Path

from dotenv import load_dotenv


def load_env():
    # load .env from the ROOT of the repo
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)
    return os.getenv
