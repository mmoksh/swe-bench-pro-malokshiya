# Google Play Scraper Search API
The repo is used to scrap the google play store for apps and their metadata. The API is used to search for apps based on different criteria such as name, category, and rating. The API returns a list of apps with their metadata such as name, description, and rating.

There is an issue with the library's search API. When searching for "Lazanda" with language "en" and country "US", the library returns empty results, but searching on the browser actually returns the app. This is a bug in the library's search API, and it might be related to a recent changes on Google Play's APIs that broke the library. Your job is to find the root cause of the issue and fix it.
