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
import logging
from urllib.parse import urlparse
from typing import Any, Optional, List
from src.utility import json_utility, requests_utility, time_utility


class CivitaiAPIWrapper(object):
    """
    Class, representing civitai API wrapper.
    """

    def __init__(self, 
                 api_key: str = None, 
                 wait_time: float = 1.5, 
                 response_output_path: str | None = None, 
                 logger_overwrite: Any = None) -> None:
        """
        Initiation method.
        :param api_key: Civitai API key which can be created in the civitai user account settings.
        :param wait_time: Waiting time in seconds between requests or download tries.
        :param response_output_path: Folder path to backup raw responses.
            Defaults to None in which case raw response content is not backed up.
        :param logger_overwrite: Logger overwrite for logging progress.
            Defaults to None in which case the progress is not logged.
        """
        self.logger = logging.Logger("[CivitaiAPIWrapper]") if logger_overwrite is None else logger_overwrite
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
                self.logger.info(f"Fetched metadata: {metadata}.")
                next_url = metadata.get("nextPage")
                if next_url:
                    if "limit=" not in next_url:
                        next_url += "&limit=100"
                    if "nsfw=" not in next_url:
                        next_url += "&nsfw=true"
                callback(data["items"])
            else:
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
        self.logger.info(
            f"Fetching data for '{url}'...")
        resp = requests.get(url, headers=self.headers)
        try:
            data = json.loads(resp.content)
            if data is not None and not "error" in data:
                self.logger.info(f"Fetching content was successful.")
                if self.response_path:
                    json_utility.save(data, os.path.join(self.response_path, time_utility.get_timestamp() + ".json"))
                return data
            else:
                self.logger.warning(f"Fetching metadata failed.")
        except json.JSONDecodeError:
            self.logger.warning(f"Response content could not be deserialized.")
            if current_try < max_tries:
                sleep(self.wait*2)
                return self.safely_fetch_api_data(url, current_try+1, max_tries=max_tries)
            else:
                return {}

    def download_asset(self, asset_url: str, output_path: str) -> None:
        """
        Abstract method for downloading an asset.
        :param asset_url: Asset URL.
        :param output_path: Output path.
        """
        #TODO: Test and refine for different asset types.
        requests_utility.download_web_asset(
            asset_url, output_path=output_path, headers=self.headers)