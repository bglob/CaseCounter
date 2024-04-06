import requests

def get_steam_inventory_count(user_id, app_id, steam_api_key):
    """
    Get the total item count of a user's Steam inventory for a specific game.
    
    :param user_id: The Steam ID of the user.
    :param app_id: The application ID for the game (e.g., 730 for CS:GO).
    :param steam_api_key: Your Steam Web API key.
    :return: The total item count or a message indicating an error or empty inventory.
    """
    url = f"http://api.steampowered.com/IEconItems_{app_id}/GetPlayerItems/v0001/"
    params = {
        'key': steam_api_key,
        'steamid': user_id,
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('result', {}).get('status') == 1:
            total_items = len(data.get('result', {}).get('items', []))
            return f"Total items in inventory: {total_items}"
        else:
            return "Failed to get inventory items. Status code not 1."
    else:
        return f"Error querying Steam API. HTTP Status Code: {response.status_code}"

# Example usage
steam_api_key = "YOUR_STEAM_API_KEY_HERE"
user_id = "STEAM_USER_ID_HERE"
app_id = 730  # Example for CS:GO
print(get_steam_inventory_count(user_id, app_id, steam_api_key))