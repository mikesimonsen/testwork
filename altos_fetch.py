from flask import Flask, render_template, request
import requests
from geopy.geocoders import Nominatim
from urllib.parse import urlencode

app = Flask(__name__)

# Replace with the actual Altos API endpoints and add any necessary authentication details.
ALTOS_LOCATION_API_URL = "https://altos.re/api/v2/reports"  # First API call URL
ALTOS_DATA_API_URL = "https://altos.re/api/v2/data"          # Second API call URL
API_KEY = "a4e9baf7"  # if required by the API
## do I also want to define the stat params up here?

def fetch_location_data(city, state, zip_code):
    """
    Call the Altos API with city, state, and zip to retrieve a location hash and URL.
    Adjust parameters and endpoint according to the API documentation.
    """
    params = {
        "city": city,
        "state": state,
        "zip": zip_code,
        "pai": API_KEY,
    }
     # Construct the URL with properly encoded query parameters.
    url_with_params = f"{ALTOS_LOCATION_API_URL}?{urlencode(params)}"
    print("Request URL:", url_with_params)
    response = requests.get(url_with_params)
    print("Response text:", response.text)
    if response.ok:
        try:
            return response.json()
        except ValueError as e:
            print("JSON decode error:", e)
            return {}
    else:
        return {}


def fetch_median_price(location_hash):
    # Build the parameters as required by the Altos Data API.
    params = {
        "hash": location_hash,
        "stat": "price_median",
        "resTypeId": 100,
        "quartile": 0,
        "window_size": "7D",
        "remove_null": "true",
        "limit": 1
    }

    url_with_params = f"{ALTOS_DATA_API_URL}?{urlencode(params)}"
    print("Requesting Data URL:", url_with_params)

    response = requests.get(url_with_params)

    if response.ok:
        try:
            json_data = response.json()
            data_dict = json_data.get("data", {})
            if data_dict:
                # Retrieve the single value from the dictionary.
                raw_price = next(iter(data_dict.values()))
                # Format as dollars: no decimals and comma separators.
                median_price = "${:,.0f}".format(raw_price)
                return median_price
            else:
                return "N/A"
        except ValueError as e:
            print("JSON decode error:", e)
            return "N/A"
    else:
        print("Request failed with status code:", response.status_code)
        return "N/A"



def geocode_address(city, state, zip_code):
    """
    Use geopy to geocode the provided address into latitude and longitude.
    """
    geolocator = Nominatim(user_agent="real_estate_app")
    address = f"{city}, {state} {zip_code}"
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

@app.route("/", methods=["GET", "POST"])
def index():
    result = {}
    lat, lon = None, None
    if request.method == "POST":
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")

        # First API call: Get location hash and URL.
        loc_data = fetch_location_data(city, state, zip_code)
        location_hash = loc_data.get("id")
        location_url = loc_data.get("url", "N/A")


        # Second API call: Use location hash to get median price.
        median_price = fetch_median_price(location_hash) if location_hash else "N/A"

        # Get coordinates for the map marker using geocoding.
        lat, lon = geocode_address(city, state, zip_code)

        result = {
            "city": city,
            "state": state,
            "zip": zip_code,
            "location_hash": location_hash,
            "location_url": location_url,
            "median_price": median_price,
        }

    return render_template("index.html", result=result, lat=lat, lon=lon)

if __name__ == '__main__':
    app.run(debug=True)
