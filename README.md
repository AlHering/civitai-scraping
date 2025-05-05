# civitai-scraping
A collection of scripts for CivitAI scraping.

# Installation & Usage
- Download Python and create a virtual environment 
- Install the requirements
- take a look into `easy_api_example.py` and adjust the `api_key` variable
- run the script to fetch the requested data and print out the fetched models, model versions, download links and the next API page
- a `response.json` is created upon successful request, take a look into it to better understand the response structure

# Further functionality
Before running any further scripts, make sure you added your API key under `src/configuration/config.py`.
Take a look at the bottom of the script. If there is a `if __name__ == "__main__":` section, it will contain further info on basic configuration.

- `src/model/civitai_api_wrapper.py` contains the `CivitaiAPIWrapper` for easier parameterized access
    - take a look at the `collect_assets_via_api` method for fetching cycle with a callback function to handle fetched entries
    - take a look at the `safely_fetch_api_data` method for handling errors in request loops
- `scrape_full_metadata.py` contains the `MetadataScraper` for scraping models and image metadata into a database (`src/database/basic_sqlalchemy_interface.py` and `src/database/data_model.py`)
    - the `scrape_to_database` method creates a callback depending on the target asset (models or images) and uses the `CivitaiAPIWrapper` to loop through requests accordingly
    - the `import_response_folder` method allows to import entries from raw responses, if they are backed up
- `enrich_model_folder.py` contains functionality to download metadata for already downloaded models (e.g. safetensor files)
    - the `download_data_for_model_file` method will create a hash for each model file and utilize a `CivitaiAPIWrapper` to download model version metadata, model metadata, and a cover image (allowed file extensions and cover image extensions can be found at the top of the file)
