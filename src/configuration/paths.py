# -*- coding: utf-8 -*-
"""
****************************************************
*               Civitai Scraping                   *
*           (c) 2025 Alexander Hering              *
****************************************************
"""
import os


PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
DATA_FOLDER = os.path.join(PROJECT_FOLDER, "data")

RAW_RESPONSE_FOLDER = os.path.join(DATA_FOLDER, "raw_responses")
DATABASE_FOLDER = os.path.join(DATA_FOLDER, "database")
IMAGE_FOLDER = os.path.join(DATA_FOLDER, "images")


for folder in [RAW_RESPONSE_FOLDER, DATABASE_FOLDER, IMAGE_FOLDER]:
    os.makedirs(folder, exist_ok=True)