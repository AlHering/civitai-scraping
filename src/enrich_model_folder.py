# -*- coding: utf-8 -*-
"""
****************************************************
*               Civitai Scraping                   *
*           (c) 2025 Alexander Hering              *
****************************************************
"""
import os
from typing import Any, Optional, Tuple
from src.utility import json_utility, hashing_utility, image_utility, internet_utility
from src.model.civitai_api_wrapper import CivitaiAPIWrapper
from src.configuration.paths import RAW_RESPONSE_FOLDER, DATA_FOLDER


MODEL_EXTENSIONS = [".safetensors", ".ckpt", ".pt", ".zip", ".pth"]
IMG_WIDTHS = [1080, 720, 576, 480]
IMG_EXTS = [".jpeg", ".jpg", ".png"]


def fix_image_url(image_data: dict, width: int = None) -> str:
    """
    Tries to fix civitai image URLs.
    :param image_data: Image data.
    :param width: Forced width to use.
    :return: Fixed image URL.
    """
    img_url_parts = image_data["url"].split("/")
    for index, part in enumerate(img_url_parts):
        if part.startswith("width="):
            img_url_parts[index] = f"width={image_data['width'] if width is None else width}"
    return "/".join(img_url_parts)


def download_data_for_model_file(wrapper: CivitaiAPIWrapper,
                                 model_file_path: str,
                                 skip_filename_check: bool = True,
                                 save_model_metadata: bool = True,
                                 save_hash: bool = True,
                                 save_cover_image: bool = True) -> Tuple[Optional[str], Optional[dict], Optional[dict], Optional[str]]:
    """
    Downloads additional data for model file.
    :param wrapper: API wrapper.
    :param model_file_path: Path of the model file.
    :param skip_filename_check: Flag for declaring whether to skip filename checks (only check file hash).
        Defaults to true.
    :param save_model_metadata: Flag for declaring whether to save model metadata.
        Defaults to true.
    :param save_hash: Flag for declaring whether to save hash.
        Defaults to true.
    :param save_cover_image: Flag for declaring whether to save cover image.
        Defaults to true.
    :return: Hash, model version metadata, model metadata and cover image path.
    """
    # check preconditions
    if os.path.isfile(model_file_path):
        directory, file = os.path.split(model_file_path)
        file_name, file_extension = os.path.splitext(file)
    else:
        wrapper.logger.warning(f"File '{model_file_path}' does not exist, skipping...")
        return None, None, None, None

    if file_extension.lower() not in MODEL_EXTENSIONS:
        wrapper.logger.warning(f"File extension of '{model_file_path}' is not in {MODEL_EXTENSIONS}, skipping...")
        return None, None, None, None
    
    model_hash_path = os.path.join(directory, f"{file_name}.hash")
    model_version_metadata_path = os.path.join(directory, f"{file_name}_model_version.json")
    model_metadata_path = os.path.join(directory, f"{file_name}_model.json")

    # handle hash
    if not os.path.exists(model_hash_path):
        hash = hashing_utility.hash_with_sha256(model_file_path)
        if save_hash:
            open(model_hash_path, "w").write(hash)
    else:
        hash = open(model_hash_path, "r").read()  
            
    # handle model version metadata
    if not os.path.exists(model_version_metadata_path):
        model_version_metadata = wrapper.safely_fetch_api_data(wrapper.model_version_by_hash_endpoint + f"/{hash}?nsfw=true")
        if model_version_metadata:
            if (skip_filename_check or any(entry["name"] == file for entry in model_version_metadata["files"])):
                json_utility.save(model_version_metadata, model_version_metadata_path)
            wrapper.logger.warning(f"Found metadata, but file name is not in {[entry['name'] for entry in model_version_metadata['files']]}")
    else:
        model_version_metadata = json_utility.load(model_version_metadata_path)

    # handle model metadata
    if not os.path.exists(model_metadata_path) and model_version_metadata:
        model_metadata = wrapper.safely_fetch_api_data(f"{wrapper.model_api_endpoint}/{model_version_metadata['modelId']}")
        if model_metadata and save_model_metadata:
            json_utility.save(model_metadata, model_metadata_path)
    else:
        model_metadata = json_utility.load(model_metadata_path)

    # handle cover image
    if save_cover_image and model_version_metadata:
        image_path = wrapper.download_image_for_model_file(
            directory=directory,
            file_name=file_name,
            model_version_metadata=model_version_metadata
        )

    return hash, model_version_metadata, model_metadata, image_path

def download_image_for_model_file(wrapper: CivitaiAPIWrapper, 
                                  directory: str, 
                                  file_name: str, 
                                  model_version_metadata: dict) -> str | None:
    """
    Downloads cover image for model file.
    :param wrapper: API wrapper.
    :param directory: Target directory for image file.
    :param file_name: Image file name, preferably model file name (without extension).
    :param model_version_metadata: Model version metadata.
    :return: Image file path, if download was successful.
    """
    if model_version_metadata.get("images", False):
        options = [img for img in model_version_metadata["images"] if img.get("type", "image") != "video"]
        if options:
            image_data = options[0]
            image_url_parts = image_data["url"].replace("https://image.civitai.com/", "").split("/")
            image_file_ext = os.path.splitext(image_url_parts[-1])[1]
            if image_file_ext not in IMG_EXTS and wrapper.logger:
                wrapper.logger.warning(f"Unsupported extension for image download: '{image_file_ext}'")
            else:
                image_path = os.path.join(directory, f"{file_name}{image_file_ext}")
                tries = 0
                while not image_utility.check_image_health(image_path) and tries <= len(IMG_WIDTHS):
                    wrapper.logger.info(f"'{image_path}' not existing or invalid, downloading ...")
                    if not wrapper.download_asset(
                        asset_url=fix_image_url(image_data, width=None if tries == 0 else IMG_WIDTHS[tries - 1]),
                        output_path=image_path):
                        while not internet_utility.check_connection():
                            wrapper.logger.info(f"Waiting for internet connection...")
                            internet_utility.wait_for_connection()
                        tries += 1
                if not os.path.exists(image_path):
                    image_path = None
            return image_path
    return None


if __name__ == "__main__":
    # Create an API key via civitai user account settings and replace "YourAPIkey" below
    wrapper = CivitaiAPIWrapper(
        api_key="YourAPIkey",
        response_output_path=RAW_RESPONSE_FOLDER
    )
    # Replace DATA_FOLDER by your model folder below to start downloading metadata for the model files in this folder
    for root, dirs, files in os.walk(DATA_FOLDER, topdown=True):
        for file in files:
            download_data_for_model_file(
                wrapper=wrapper,
                model_file_path=os.path.join(root, file)
            )
