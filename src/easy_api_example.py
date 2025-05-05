# -*- coding: utf-8 -*-
"""
****************************************************
*                CivitAI Scraping                  *
*            (c) 2025 Alexander Hering             *
****************************************************
"""
import requests
import json
from src.utility import json_utility

# API Documentation: https://developer.civitai.com/docs/api/public-rest

# Authorization via API key or token parameter: https://developer.civitai.com/docs/api/public-rest#authorization
api_key = "MY_API_KEY" 
headers = {"Authorization": "Bearer " + api_key}

# URLs
models_base_url = "https://civitai.com/api/v1/models"

# Query parameter stack for models: https://developer.civitai.com/docs/api/public-rest#get-apiv1models
# E.g. sort models by newest, fetch first 20 entries, allow nsfw content
models_params = "?sort=Newest&limit=20&nsfw=true"

# Fetch model metadata and save it to file
resp = requests.get(models_base_url + models_params, headers=headers)
data = json.loads(resp.content)
json_utility.save(data=data, path="response.json")

# Response data always contains "items" with the list of requested entries, and "metadata"
# The response "metadata" contains a cursor and the next page under "nextPage"
# Requesting the next page as seen above will yield the next 20 model entries under the given parameter conditions
for model_entry in data["items"]:
    print(f"Model {model_entry['id']}: {model_entry['name']}")
    for model_version_entry in model_entry["modelVersions"]:
        print(f"\tModelversion {model_version_entry['id']}: {model_version_entry['name']} ({model_version_entry['baseModel']})")