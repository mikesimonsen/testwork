from flask import Flask, render_template, request
import requests
from geopy.geocoders import Nominatim
from urllib.parse import urlencode

app = Flask(__name__)

ALTOS_LOCATION_API_URL = "https://altos.re/api/v2/reports"
ALTOS_DATA_API_URL = "https://altos.re/api/v2/data"
API_KEY = "a4e9baf7"

def fetch_location_data(city, state, zip_code):
    params = {
        "city": city,
        "state": state,
        "zip": zip_code,
        "pai": API_KEY,
    }
    url_with_params = f"{ALTOS_LOCATION_API_URL}?{urlencode(params)}"
    print("Requesting location URL:", url_with_params)
    response = requests.get(url_with_params)
    if response.ok:
        try:
            return response.json()
        except ValueError as e:
            print("JSON decode error in location data:", e)
            return {}
    else:
        print("Location API request failed with status code:", response.status_code)
        return {}

def fetch_median_price(location_hash):
    params = {
        "hash": location_hash,
        "stat": "price_median",
        "resTypeId": 100,
        "quartile": 0,
        "window_size": "7D",
        "remove_null": "true",
        "limit": 157
    }

    url_with_params = f"{ALTOS_DATA_API_URL}?{urlencode(params)}"
    print("Requesting data URL:", url_with_params)

    response = requests.get(url_with_params)

    if response.ok:
        try:
            json_data = response.json()
            data_dict = json_data.get("data", {})
            if data_dict:
                # Retrieve the single median price value from the dictionary.
                raw_price = next(iter(data_dict.values()))
                # Format the median price as dollars, with comma separators and no decimals.
                median_price = "${:,.0f}".format(raw_price)
                return median_price
            else:
                return "N/A"
        except ValueError as e:
            print("JSON decode error in data API:", e)
            return "N/A"
    else:
        print("Data API request failed with status code:", response.status_code)
        return "N/A"

def geocode_address(city, state, zip_code):
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
    error = None

    if request.method == "POST":
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")

        # Convert the state field to uppercase.
        state = state.upper() if state else ""

        # Validate the state against allowed two-letter state codes.
        valid_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        }

        if state not in valid_states:
            error = "Invalid state code. Please enter a valid two-letter state code."
        else:
            # First API call: Get location hash and URL.
            loc_data = fetch_location_data(city, state, zip_code)
            location_hash = loc_data.get("id")
            location_url = loc_data.get("url", "N/A")
            ## id and url are the labels in the Altos API.

            # Second API call: Use location hash to get median price.
            median_price = fetch_median_price(location_hash) if location_hash else "N/A"

            # Geocode the address for map coordinates.
            lat, lon = geocode_address(city, state, zip_code)

            result = {
                "city": city,
                "state": state,
                "zip": zip_code,
                "location_hash": location_hash,
                "location_url": location_url,
                "median_price": median_price,
            }

    return render_template("index.html", result=result, lat=lat, lon=lon, error=error)

if __name__ == '__main__':
    app.run(debug=True)
