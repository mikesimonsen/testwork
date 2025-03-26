from flask import Flask, render_template, request
import requests
from geopy.geocoders import Nominatim
from urllib.parse import urlencode

app = Flask(__name__)

ALTOS_LOCATION_API_URL = "https://altos.re/api/v2/reports"
ALTOS_DATA_API_URL = "https://altos.re/api/v2/data"
ALTOS_API_KEY = "a4e9baf7"

def fetch_location_data(city, state, zip_code):
    params = {
        "city": city,
        "state": state,
        "zip": zip_code,
        "pai": ALTOS_API_KEY,
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
        "limit": 1
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

def fetch_altos_stat(location_hash, stat_name):
    """
    Fetch a specific Altos stat (e.g., price_median, dom_mean, sqft_mean) for the given location hash.
    
    Args:
        location_hash (str): The unique ID returned from the location endpoint.
        stat_name (str): The name of the stat to retrieve (e.g., 'price_median').
    
    Returns:
        str: The formatted result (e.g., "$1,234,567") or "N/A" on error.
    """
    params = {
        "hash": location_hash,
        "stat": stat_name,
        "resTypeId": 100,
        "quartile": 0,
        "window_size": "7D",
        "remove_null": "true",
        "limit": 1,
        "pai": ALTOS_API_KEY,
    }
    
    url_with_params = f"{ALTOS_DATA_API_URL}?{urlencode(params)}"
    print(f"Requesting stat '{stat_name}' with URL:", url_with_params)
    
    response = requests.get(url_with_params)
    if response.ok:
        try:
            json_data = response.json()
            data_dict = json_data.get("data", {})
            if data_dict:
                raw_value = next(iter(data_dict.values()))

                # Format based on type of stat
                if "price" in stat_name or "sqft" in stat_name or "lot" in stat_name:
                    return "${:,.0f}".format(raw_value)
                elif "percent" in stat_name:
                    return f"{raw_value:.1f}%"
                else:
                    return "{:,.0f}".format(raw_value)
            else:
                return "N/A"
        except (ValueError, TypeError, StopIteration) as e:
            print("Error parsing response:", e)
            return "N/A"
    else:
        print("Altos API request failed:", response.status_code)
        return "N/A"


def fetch_altos_history(location_hash, stat_name, limit=153):
    """
    Fetch a longer history of a given Altos stat by increasing the limit parameter.

    Args:
        location_hash (str): The unique location hash from Altos.
        stat_name (str): The name of the stat to retrieve (e.g., 'price_median').
        limit (int): The number of historical records to retrieve (default is 153 weeks).

    Returns:
        dict: A dictionary where the keys are dates and values are the corresponding stat values.
    """
    params = {
        "hash": location_hash,
        "stat": stat_name,
        "resTypeId": 100,
        "quartile": 0,
        "window_size": "7D",
        "remove_null": "true",
        "limit": limit,
        "pai": ALTOS_API_KEY,   # Ensure ALTOS_API_KEY is defined at the top of your file.
    }
    url_with_params = f"{ALTOS_DATA_API_URL}?{urlencode(params)}"
    print("Requesting history URL:", url_with_params)
    
    response = requests.get(url_with_params)
    if response.ok:
        try:
            json_data = response.json()
            data_dict = json_data.get("data", {})
            return data_dict
        except ValueError as e:
            print("JSON decode error in fetch_altos_history:", e)
            return {}
    else:
        print("History API request failed with status code:", response.status_code)
        return {}




def geocode_address(city, state, zip_code):
    geolocator = Nominatim(user_agent="real_estate_app")
    address = f"{city}, {state} {zip_code}"
    try:
        # Increase the timeout (e.g., 10 seconds) to allow more time for the response.
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print("Geocoding error:", e)
        return None, None



from datetime import datetime

def sort_timeseries(data_dict):
    """
    Sort a dictionary of date-value pairs into a sequential time series.

    Args:
        data_dict (dict): A dictionary where keys are date strings (e.g., "YYYY-MM-DD")
                          and values are the corresponding statistic values.

    Returns:
        list of tuples: Sorted list of (date, value) tuples in chronological order.
    """
    


    try:
        # Convert the date strings to datetime objects for accurate sorting.
        sorted_items = sorted(data_dict.items(), key=lambda item: datetime.strptime(item[0], "%Y-%m-%d"))
        print("Sorted items:", sorted_items)
    except Exception as e:
        print("Error sorting timeseries:", e)
        # Fall back to unsorted items if conversion fails.
        sorted_items = list(data_dict.items())
    return sorted_items




@app.route("/", methods=["GET", "POST"])
def index():
    result = {}
    lat, lon = None, None
    error = None
    chosen_stat = None  # Hold the selected stat from the form
    history = None     # to hold historical data

    if request.method == "POST":
        city = request.form.get("city")
        state = request.form.get("state")
        zip_code = request.form.get("zip")
        chosen_stat = request.form.get("stat")  # Retrieve the selected stat from the dropdown

        # Convert state to uppercase.
        state = state.upper() if state else ""

        # Validate state against allowed two-letter state codes.
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
            # First API call: Get location data.
            loc_data = fetch_location_data(city, state, zip_code)
            location_hash = loc_data.get("id")       # Note: 'id' is the location hash.
            location_url = loc_data.get("url", "N/A")   # Note: 'url' is the location URL.
            
            # Fetch the chosen statistic using the location hash.
            stat_value = fetch_altos_stat(location_hash, chosen_stat) if location_hash else "N/A"
            
            # Fetch historical data using a larger limit (e.g., 20 records).
            if location_hash:
                raw_history = fetch_altos_history(location_hash, chosen_stat, limit=160)
                # Sort the history in chronological order.
                history = sort_timeseries(raw_history)
                print("history sorted:", history)
            # Geocode the address for map coordinates.
            lat, lon = geocode_address(city, state, zip_code)
            
            result = {
                "city": city,
                "state": state,
                "zip": zip_code,
                "location_hash": location_hash,
                "location_url": location_url,
                "stat_value": stat_value,
                "history": history
            }
    
    # Pass chosen_stat back to the template so it can be used (for example, in labels).
    return render_template("index.html", result=result, lat=lat, lon=lon, error=error, stat=chosen_stat)

if __name__ == '__main__':
    app.run(debug=True)
