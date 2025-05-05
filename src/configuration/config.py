# -*- coding: utf-8 -*-
"""
****************************************************
*               Civitai Scraping                   *
*           (c) 2025 Alexander Hering              *
****************************************************
"""
import os
from dotenv import dotenv_values
import logging
LOGGER = logging.Logger("[CivitaiScraping]")
LOGGER.setLevel(logging.INFO)


PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
ENV_PATH = os.path.join(PROJECT_FOLDER, ".env")
ENV = dotenv_values(ENV_PATH) if os.path.exists(ENV_PATH) else {}


# Authorization via API key or token parameter: https://developer.civitai.com/docs/api/public-rest#authorization
# Head to your civitai user account settings to create one
API_KEY = ENV.get("API_KEY", "MyAPIKey")


# Additional folders
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")
RAW_RESPONSE_FOLDER = os.path.join(DATA_FOLDER, "raw_responses")
DATABASE_FOLDER = os.path.join(DATA_FOLDER, "database")
IMAGE_FOLDER = os.path.join(DATA_FOLDER, "images")


for folder in [RAW_RESPONSE_FOLDER, DATABASE_FOLDER, IMAGE_FOLDER]:
    os.makedirs(folder, exist_ok=True)


if API_KEY == "MyAPIKey":
    logging.warning("The API_KEY 'MyAPIKey' in 'src/configuration/config.py' is only a placeholder, please adjust it for full functionality!")
