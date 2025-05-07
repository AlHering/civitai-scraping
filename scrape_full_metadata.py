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
import requests
from typing import List, Any
import shutil
from time import sleep
from src.database.basic_sqlalchemy_interface import BasicSQLAlchemyInterface, FilterMask
from src.database.data_model import populate_data_infrastructure, get_default_entries
from src.model.civitai_api_wrapper import CivitaiAPIWrapper
from src.configuration.config import LOGGER, API_KEY, RAW_RESPONSE_FOLDER, DATABASE_FOLDER, IMAGE_FOLDER
from src.utility import json_utility, internet_utility


class MetadataScraper(object):
    """
    Class, representing civitai metadata scraper.
    """

    def __init__(self,
                wrapper: CivitaiAPIWrapper,
                database: BasicSQLAlchemyInterface,
                image_folder: str | None = None) -> None:
            """
            Initiation method.
            :param wrapper: Civitai API wrapper.
            :param database: Database to write metadata to.
            :param image_folder: Folder to save images in.
                Defaults to None in which case images are not saved.
            """
            self.wrapper = wrapper
            self.database = database
            self.image_folder = image_folder
            if self.image_folder:
                os.makedirs(self.image_folder, exist_ok=True)

    def scrape_to_database(self, asset_type: str, start_url: str | None = None) -> None:
        """
        Scrapes metadata to database.
        :param asset_type: Asset type out of ["models", "images"].
        :param start_url: Start URL to re-enter scraping process at specific next-page cursor.
            Defaults to None in which case a new scraping process is started.
        """
        entry_url_base = {
                "models": "https://civitai.com/api/v1/models/", 
                "images": "https://civitai.com/api/v1/images/"}[asset_type]
        
        patching_method = {
                "models": self.post_or_patch_model_entry, 
                "images": self.post_or_patch_image_entry}[asset_type]

        def callback(entries: List[Any]) -> None:
            for entry in entries:
                try:
                    url = entry_url_base + str(entry["id"])
                    patching_method(url=url, entry=entry)
                except Exception as ex:
                    wrapper.logger.warning(f"Process failed for {asset_type} entry {entry['id']} ({ex})...")

        self.wrapper.scrape_available_asset_metadata(
            asset_type=asset_type, 
            callback=callback, 
            start_url=start_url
        )
         

    def post_or_patch_model_entry(self, url: str, entry: dict) -> None:
        """
        Posts or patches an entry.
        :param url: Entry URL.
        :param data: Entry data.
        """
        obj = self.database.get_objects_by_filtermasks(
                    "model", [FilterMask(
                        [["url", "==", url]])]
                )
        if obj:
            # Entry already existing, merge in new model versions if there are any
            reference_entry = obj[0].data
            patched = False
            for mv_data in reference_entry["modelVersions"]:
                if not any(updated_mv_data["id"] == mv_data["id"] for updated_mv_data in entry["modelVersions"]):
                    entry["modelVersions"].append(copy.deepcopy(mv_data))
                    patched = True
            if patched:
                print(f"\tFound additional model versions for model {entry['id']}, patching...")
                self.database.patch_object("model", obj[0].id, data=entry)
        else:
            print(f"\tFound new model {entry['id']}, adding...")
            self.database.post_object(
                "model", 
                url=url,
                source="civitai.com",
                data=entry,
                state="full")   

    @internet_utility.timeout(180.0)
    def save_image_to_disk(self, url: str, image_folder: str) -> str:
        """
        Function for downloading image to disk.
        :param url: Image URL.
        :param image_folder: Image folder.
        :return: File path.
        """
        file_path = os.path.join(image_folder, url.split("/")[-1])
        download = requests.get(url, stream=True, headers=self.wrapper.headers)
        with open(file_path, 'wb') as file:
            shutil.copyfileobj(download.raw, file)
        del download
        sleep(1)
        return file_path

    def post_or_patch_image_entry(self, url: str, entry: dict) -> None:
        """
        Posts or patches an entry.
        :param url: Entry URL.
        :param data: Entry data.
        """
        obj = self.database.get_objects_by_filtermasks(
                    "image", [FilterMask(
                        [["url", "==", url]])]
                )
        
        if not obj:
            print(f"\tFound new image {entry['id']}, adding...")
            file_path = None
            if self.image_folder:
                file_path = self.save_image_to_disk(url=entry["url"], image_folder=self.image_folder)
            self.database.post_object(
                "image", 
                url=url,
                source="civitai.com",
                data=entry,
                path=file_path,
                state="full",
            )
            
    def get_url_for_asset(self, asset_type: str, entry: dict) -> str:
        """
        Returns asset URL.
        :param asset_type: Asset type out of ["models", "images"].
        :param entry: Asset entry.
        :return: Asset URL
        """
        if asset_type == "models":
            return f"https://civitai.com/api/v1/models/{entry['id']}"
        elif asset_type == "images":
            image_url_parts =  [part for part in entry["url"].split("/") if not part.lower().startswith("width=")]
            return "/".join(image_url_parts)

    def import_response_file(self, file_path: str, asset_type: str = "models") -> None:
        """
        Imports a specific response json file.
        :param file_path: Path to response file.
        :param asset_type: Asset type out of ["models", "images"].
        """
        try:
            data = json_utility.load(file_path)
        except:
            print(f"\n\tFile {file_path} could not be loaded...\n")
            data = {}
        
        patching_method = {
                "models": self.post_or_patch_model_entry, 
                "images": self.post_or_patch_image_entry}[asset_type]
        
        try:
            if "items" in data:
                for index, entry in enumerate(tqdm(data["items"], desc=f"Importing {asset_type} entries...", unit="entry", leave=False)):
                    url = self.get_url_for_asset(asset_type=asset_type, entry=entry)
                    patching_method(url=url, entry=entry)
            elif "id" in data:
                url = self.get_url_for_asset(asset_type=asset_type, entry=entry)
                patching_method(url=url, entry=data)
            else:
                print(f"\n\tFile {file_path}: entry {entry['id']} could not be imported...\n")
        except:
            print(f"\n\tFile {file_path}: entry {entry['id']} could not be imported...\n")

    def import_response_folder(self, path: str = RAW_RESPONSE_FOLDER, asset_type: str = "models") -> None:
        """
        Imports raw response folder.
        :param path: Folder path.
        :param asset_type: Asset type out of ["models", "images"].
        """
        for root, _, files in os.walk(path):
            for file in tqdm(files, desc="Loading response files...", unit="file", leave=False):
                file_path = os.path.join(root, file)
                self.import_response_file(file_path=file_path)

    def get_cover_images(self, output_path: str) -> None:
        """
        Downloads cover images for model versions.
        :param output_path: Output path for cover images.
        """
        raise NotImplementedError("'get_cover_images' is not implemented yet.")
        with self.database.session_factory() as session:
            progress_bar = tqdm(desc="Iterating over model entries...", unit="models", total=database.get_object_count_by_type("model"), leave=False)
            for obj in session.query(database.model["model"]).yield_per(50):
                model = obj.data
                for model_version in tqdm(model["modelVersions"], desc="Iterating over model version entries...", unit="model versions", leave=False):
                    pass
                progress_bar.update()


if __name__ == "__main__":
    # Create an API key via civitai user account settings and replace "MyAPIKey" under src/configuration/config.py
    wrapper = CivitaiAPIWrapper(
        api_key=API_KEY,
        response_output_path=RAW_RESPONSE_FOLDER,
        logger_overwrite=LOGGER
    )
    database = BasicSQLAlchemyInterface(
        working_directory=DATABASE_FOLDER,
        population_function=populate_data_infrastructure,
        default_entries=get_default_entries(),
    )
    # Set an image folder below to download images while fetching metadata
    scraper = MetadataScraper(
        wrapper=wrapper,
        database=database,
        image_folder=None
    )
    # Set "models" or "images" below to scrape the corresponding metadata to database
    scraper.scrape_to_database(asset_type="models", start_url=None)

    

    