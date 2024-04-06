import requests

def get_inventory_with_cookies(user_id, app_id, cookies):
    """
    Fetch a user's inventory using session cookies for authentication.
    
    :param user_id: The Steam user's ID.
    :param app_id: The application ID for the game.
    :param cookies: A dictionary of session cookies obtained from a manual login.
    :return: Inventory data or an error message.
    """
    url = f"https://steamcommunity.com/inventory/{user_id}/{app_id}/2?l=english&count=5000"
    headers = {'Cookie': '; '.join([f'{key}={value}' for key, value in cookies.items()])}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Failed to retrieve inventory. Status code: {response.status_code}"

# Example usage with dummy data
cookies = {
    'steamLoginSecure': 'your_steamLoginSecure_value_here',
    # Include other necessary cookies
}

user_id = '76561198000000000'  # Example SteamID64
app_id = 730  # Example App ID for CS:GO

inventory_data = get_inventory_with_cookies(user_id, app_id, cookies)
print(inventory_data)