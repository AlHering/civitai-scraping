# -*- coding: utf-8 -*-
"""
****************************************************
*          Basic Language Model Backend            *
*         (c) 2023-2025 Alexander Hering           *
****************************************************
"""
import os
import requests
import json
from time import sleep
from urllib.parse import urlparse
from typing import Any, Optional, List, Tuple
from src.utility import json_utility, requests_utility, hashing_utility, image_utility, internet_utility
from src.utility import file_system_utility


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


class CivitaiAPIWrapper(object):
    """
    Class, representing civitai API wrapper.
    """

    def __init__(self, 
                 api_key: str = None, 
                 wait_time: float = 2.8, 
                 response_output_path: str | None = None, 
                 logger: Any = None) -> None:
        """
        Initiation method.
        :param api_key: Civitai API key which can be created in the civitai user account settings.
        :param wait_time: Waiting time in seconds between access or download tries.
        :param response_output_path: Folder path to backup raw responses.
            Defaults to None in which case raw response content is not backed up.
        :param logger: Logger for logging progress.
            Defaults to None in which case the progress is not logged.
        """
        self.logger = logger
        self.api_key = api_key
        self.headers = {"Authorization": "Bearer " + self.api_key}
        self.base_url = "https://civitai.com/"
        self.api_base_url = f"{self.base_url}api/v1"
        self.model_version_api_endpoint = f"{self.api_base_url}/model-versions"
        self.model_version_by_hash_endpoint = f"{self.model_version_api_endpoint}/by-hash"
        self.model_api_endpoint = f"{self.api_base_url}/models"
        self.image_api_endpoint = f"{self.api_base_url}/images"
        self.wait = wait_time
        self.response_path = response_output_path
        if response_output_path:
            os.makedirs(response_output_path, exist_ok=True)

    def get_source_name(self) -> str:
        """
        Classmethod for retrieving source name.
        :return: Source name.
        """
        return "civitai.com"

    def check_connection(self, **kwargs: Optional[dict]) -> bool:
        """
        Method for checking connection.
        :param kwargs: Arbitrary keyword arguments.
        :return: True if connection was established successfully else False.
        """
        result = requests.get(self.base_url).status_code == 200
        if self.logger is not None:
            self.logger.info("Connection was successfully established.") if result else self.logger.warning(
            "Connection could not be established.")
        return result

    def validate_url_responsibility(self, url: str) -> bool:
        """
        Method for validating the responsibility for a URL.
        :param url: Target URL.
        :return: True, if wrapper is responsible for URL else False.
        """
        return urlparse(url).netloc in self.base_url

    def scrape_available_asset_metadata(self, asset_type: str, **kwargs: Optional[dict]) -> List[dict]:
        """
        Abstract method for acquiring available metadata entries for a target asset type.
        :param asset_type: Asset type out of ["models", "images"].
        :param kwargs: Arbitrary keyword arguments.
            'callback': A callback for adding batches of scraping results while scraping process runs.
                If a callback for adding results is given, this method will return an empty list.
            'start_url': A starting URL for cursor pagination.
        :return: List of entries of given target type.
        """
        result = []
        callback = kwargs.get("callback")
        if callback is None:
            def callback(x: Any) -> None: result.extend(
                x) if isinstance(x, list) else result.append(x)

        self.collect_assets_via_api(asset_type=asset_type, callback=callback, start_url=kwargs.get("start_url"))
        return result

    def collect_assets_via_api(self, asset_type: str, callback: Any, start_url: str | None = None) -> None:
        """
        Method for collecting assets data via api.
        :param asset_type: Asset type out of ["models", "images"].
        :param callback: Callback to call with collected model data batches.
        :param start_url: A starting URL for cursor pagination.
        """
        if start_url:
            next_url = start_url
        else:
            next_url = {
                "models": f"{self.model_api_endpoint}?sort=Newest&nsfw=true&limit=100", 
                "images": f"{self.image_api_endpoint}?sort=Newest&nsfw=true&limit=100"}[asset_type]
        while next_url:
            sleep(self.wait)
            data = self.safely_fetch_api_data(next_url, current_try=1)
            next_url = False
            if isinstance(data, dict):
                metadata = data["metadata"]
                if self.logger is not None:
                    self.logger.info(f"Fetched metadata: {metadata}.")
                next_url = metadata.get("nextPage")
                if next_url:
                    if "limit=" not in next_url:
                        next_url += "&limit=100"
                    if "nsfw=" not in next_url:
                        next_url += "&nsfw=true"
                callback(data["items"])
            else:
                if self.logger is not None:
                    self.logger.warning(f"Fetched data is no dictionary: {data}")

    def safely_fetch_api_data(self, url: str, current_try: int = 3, max_tries: int = 3) -> dict:
        """
        Method for fetching API data.
        :param url: Target URL.
        :param current_try: Current try.
            Defaults to 3, which results in a single fetching try with max_tries at 3.
        :param max_tries: Maximum number of tries.
            Defaults to 3.
        :return: Fetched data or empty dictionary.
        """
        if self.logger is not None:
            self.logger.info(
                f"Fetching data for '{url}'...")
        resp = requests.get(url, headers=self.headers)
        try:
            data = json.loads(resp.content)
            if data is not None and not "error" in data:
                if self.logger is not None:
                    self.logger.info(f"Fetching content was successful.")
                if self.response_path:
                    json_utility.save(data, os.path.join(self.response_path, file_system_utility.clean_directory_name(url) + ".json"))
                return data
            else:
                if self.logger is not None:
                    self.logger.warning(f"Fetching metadata failed.")
        except json.JSONDecodeError:
            if self.logger is not None:
                self.logger.warning(f"Response content could not be deserialized.")
            if current_try < max_tries:
                sleep(self.wait)
                return self.safely_fetch_api_data(url, current_try+1, max_tries=max_tries)
            else:
                return {}

    def download_asset(self, asset_url: str, output_path: str) -> None:
        """
        Abstract method for downloading an asset.
        :param asset_url: Asset URL.
        :param output_path: Output path.
        """
        requests_utility.download_web_asset(
            asset_url, output_path=output_path, headers=self.headers)
        
    def fetch_or_create_missing_model_files(self, 
                                            folder_path: str) -> List[Tuple[Optional[str], Optional[dict], Optional[dict], Optional[str]]]:
        """
        Fetching or creates missing model files.
        :param folder_path: Path to model folder.
        :return: Tuple of hash, model version metadata, model metadata and cover image path.
        """
        results = []
        for root, dirs, files in os.walk(folder_path, topdown=True):
            for file in files:
                results.append(self.download_data_for_model_file(os.path.join(root, file)))
        return results
    
    def download_data_for_model_file(self,
                                     model_file_path: str,
                                     skip_filename_check: bool = True,
                                     save_model_metadata: bool = True,
                                     save_hash: bool = True,
                                     save_cover_image: bool = True) -> Tuple[Optional[str], Optional[dict], Optional[dict], Optional[str]]:
        """
        Downloads model metadata for model file.
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
            if self.logger:
                self.logger.warning(f"File '{model_file_path}' does not exist, skipping...")
            return None, None, None, None

        if file_extension.lower() not in MODEL_EXTENSIONS:
            if self.logger:
                self.logger.warning(f"File extension of '{model_file_path}' is not in {MODEL_EXTENSIONS}, skipping...")
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
            model_version_metadata = self.safely_fetch_api_data(self.model_version_by_hash_endpoint + f"/{hash}?nsfw=true")
            if model_version_metadata:
                if (skip_filename_check or any(entry["name"] == file for entry in model_version_metadata["files"])):
                    json_utility.save(model_version_metadata, model_version_metadata_path)
                elif self.logger:
                    self.logger.warning(f"Found metadata, but file name is not in {[entry['name'] for entry in model_version_metadata['files']]}")
        else:
            model_version_metadata = json_utility.load(model_version_metadata_path)

        # handle model metadata
        if not os.path.exists(model_metadata_path) and model_version_metadata:
            model_metadata = self.safely_fetch_api_data(f"{self.model_api_endpoint}/{model_version_metadata['modelId']}")
            if model_metadata and save_model_metadata:
                json_utility.save(model_metadata, model_metadata_path)
        else:
            model_metadata = json_utility.load(model_metadata_path)

        # handle cover image
        if save_cover_image and model_version_metadata:
            image_path = self.download_image_for_model_file(
                directory=directory,
                file_name=file_name,
                model_version_metadata=model_version_metadata
            )

        return hash, model_version_metadata, model_metadata, image_path
    
    def download_image_for_model_file(self, 
                                      directory: str, 
                                      file_name: str, 
                                      model_version_metadata: dict) -> str | None:
        """
        Downloads cover image for model file.
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
                if image_file_ext not in IMG_EXTS and self.logger:
                    self.logger.warning(f"Unsupported extension for image download: '{image_file_ext}'")
                else:
                    image_path = os.path.join(directory, f"{file_name}{image_file_ext}")
                    tries = 0
                    while not image_utility.check_image_health(image_path) and tries <= len(IMG_WIDTHS):
                        if self.logger:
                            self.logger.info(f"'{image_path}' not existing or invalid, downloading ...")
                        if not self.download_asset(
                            asset_url=fix_image_url(image_data, width=None if tries == 0 else IMG_WIDTHS[tries - 1]),
                            output_path=image_path):
                            while not internet_utility.check_connection():
                                if self.logger:
                                    self.logger.info(f"Waiting for internet connection...")
                                internet_utility.wait_for_connection()
                            tries += 1
                    if not os.path.exists(image_path):
                        image_path = None
                return image_path
        return None