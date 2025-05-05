# -*- coding: utf-8 -*-
"""
****************************************************
*               Civitai Scraping                   *
*           (c) 2025 Alexander Hering              *
****************************************************
"""
import os
import copy
from tqdm import tqdm
import logging
import requests
from typing import List, Any, Set
import shutil
from tqdm import tqdm
from time import sleep
from sqlalchemy import func, and_, or_
from src.database.basic_sqlalchemy_interface import BasicSQLAlchemyInterface, FilterMask
from src.database.data_model import populate_data_infrastructure, get_default_entries
from src.model.civitai_api_wrapper import CivitaiAPIWrapper
from src.configuration.config import API_KEY, LOGGER, PROJECT_FOLDER, DATABASE_FOLDER, IMAGE_FOLDER
from src.utility import json_utility, internet_utility


MODEL_TYPES = {'LORA', 'Upscaler', 'VAE', 'Hypernetwork', 'LoCon', 'Wildcards', 'Controlnet', 'Checkpoint', 'Other', 'AestheticGradient', 'Detection', 'DoRA', 'MotionModule', 'TextualInversion', 'Poses', 'Workflows'}


def fetch_model_entries_by_type(database: BasicSQLAlchemyInterface, model_type: str | None = None) -> List[dict]:
    """
    Fetches only lora model entries.
    :param database: Database.
    :param model_type: Target model type.
    :return: Model entries.
    """
    with database.session_factory() as session:
        result = session.query(database.model["model"]).filter(func.json_extract(database.model["model"].data, "$.type") == model_type).all()
    return [obj.data for obj in result]


def fetch_all_model_types(database: BasicSQLAlchemyInterface) -> Set:
    """
    Collects all distinct model types.
    :param database: Database.
    :return: Set of model types.
    """
    available_types = set()
    with database.session_factory() as session:
        progress_bar = tqdm(desc="Iterating over model entries...", unit="models", total=database.get_object_count_by_type("model"), leave=False)
        for obj in session.query(database.model["model"]).yield_per(100):
            available_types.add(obj.data["type"])
            progress_bar.update()
    return available_types


def count_model_versions(database: BasicSQLAlchemyInterface, model_type: str | None = None) -> int:
    """
    Counts model versions.
    :param database: Database.
    :param model_type: Target model type.
        Defaults to None in which case all model versions are counted.
    :return: Model version count.
    """
    counter = 0
    with database.session_factory() as session:
        progress_bar = tqdm(desc=f"Iterating over model entries {' searching for ' + model_type + 's' if model_type else ''}...", unit="models", total=database.get_object_count_by_type("model"), leave=False)
        for obj in session.query(database.model["model"]).filter((model_type is None) or (func.json_extract(database.model["model"].data, "$.type") == model_type)).yield_per(100):
            counter+=len(obj.data["modelVersions"])
            progress_bar.update()
    return counter


if __name__ == "__main__":
    database = BasicSQLAlchemyInterface(
        working_directory="/mnt/Workspaces/Data/websites/civitai",#DATABASE_FOLDER,
        population_function=populate_data_infrastructure,
        default_entries=get_default_entries(),
    )

    models_count = database.get_object_count_by_type("model")
    LOGGER.info(f"Available model types: {fetch_all_model_types(database=database)}.")
    LOGGER.info(f"Number of model entries: {models_count}")
    LOGGER.info(f"Number of model version entries: {count_model_versions(database=database)}")
    LOGGER.info(f"Number of checkpoint model version entries: {count_model_versions(database=database, model_type='Checkpoint')}")
    LOGGER.info(f"Number of LoRA model version entries: {count_model_versions(database=database, model_type='LORA')}")


