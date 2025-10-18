import requests
from config import OMDB_API_URL

class OMDbClient:
    """A client to interact with the OMDb API."""
    def __init__(self, api_key: str):
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("API key is missing or invalid. Please set it in the .env file.")
        self.api_key = api_key

    def fetch_movie_data(self, title: str) -> dict:
        """
        Fetches movie data for a given title, including full plot.

        Args:
            title: The title of the movie or series to search for.

        Returns:
            A dictionary containing the API response.
        """
        # Request full plot by adding 'plot': 'full'
        params = {"t": title, "apikey": self.api_key, "plot": "full"}
        try:
            response = requests.get(OMDB_API_URL, params=params, timeout=5)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.Timeout:
            return {"Response": "False", "Error": "The request timed out."}
        except requests.exceptions.RequestException as e:
            return {"Response": "False", "Error": f"Network Error: {e}"}