import requests
import json
import time

assets = []
totalWinter = 0

def load_cookies_from_file(filepath):
    """
    Load cookies from a given JSON file.
    
    :param filepath: Path to the JSON file containing cookies.
    :return: A dictionary of cookies.
    """
    with open(filepath, 'r') as file:
        cookies = json.load(file)
    return cookies

def get_inventory_with_cookies(user_id, app_id, cookies):
    """
    Fetch a user's inventory using session cookies for authentication.
    
    :param user_id: The Steam user's ID.
    :param app_id: The application ID for the game.
    :param cookies: A dictionary of session cookies obtained from a manual login.
    :return: Inventory data or an error message.
    """
    items = []
    url = f"https://steamcommunity.com/inventory/{user_id}/{app_id}/2?l=english&count=5000"
    start_assetid = None
    has_more_items = True

    first_run = True

    failures = 0

    while (has_more_items):
        if start_assetid:
            current_url = f"{url}&start_assetid={start_assetid}"
        else:
            current_url = url

        headers = {'Cookie': '; '.join([f'{key}={value}' for key, value in cookies.items()])}
        print("URL this time: " + current_url)
        response = requests.get(current_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            global assets
            if (first_run == True):
                assets = data.get('assets', [])
            else:
                assets.extend(data.get('assets', []))
            for item in data.get('descriptions', []):
                already_added = False
                for tag in item.get('tags'):
                    if tag.get("localized_tag_name") == "Crate" and already_added == False:
                        if 'actions' in item:
                            del item['actions']
                        if 'market_actions' in item:
                            del item['market_actions']
                        if is_unique(item, items):
                            items.append(item)
                        already_added = True
            has_more_items = data.get("more_items", False)
            start_assetid = data.get("last_assetid")
        else:
            if (failures >= 15):
                return "Error, too many bad requests"
            print("bad req happened 1x")
            failures += 1
        first_run = False
        time.sleep(0.5)
    
    
    return items

def is_unique(new_dict, dict_list):
    for existing_dict in dict_list:
        if existing_dict == new_dict:
            return False
    return True

def count_occurrences(i_id, c_id):
    number_of_occurrences = 0
    # print(assets)
    for asset in assets:
        # print("Starting loop iteration")
        # print("i id:"+i_id)
        # print("c id:"+c_id)
        # print("real i id:"+asset.get("instanceid"))
        # print("real c id:"+asset.get("classid"))
        if asset.get("classid") == c_id and asset.get("instanceid") == i_id:
            number_of_occurrences += int(asset.get("amount"))
    return number_of_occurrences


def parse_items(items):
    """
    Fetch a user's inventory using session cookies for authentication.
    
    :param user_id: The Steam user's ID.
    :param app_id: The application ID for the game.
    :param cookies: A dictionary of session cookies obtained from a manual login.
    :return: Inventory data or an error message.
    """
    x = 0
    counting_things = dict()


    # item = items[0]
    for item in items:
        i_id = item.get("instanceid")
        c_id = item.get("classid")
        
        howMany = count_occurrences(i_id,c_id)

        is_crate = ("" != item.get("type"))

        dictName = ""

        if (is_crate):
            dictName = item.get("name")
            if (dictName in counting_things.keys()):
                # print("Did incrementing on '" + dictName + "'")
                counting_things[dictName] += howMany
            else:
                counting_things[dictName] = howMany
        else:
            for tag in item.get("tags"):
                if tag.get("localized_category_name") == "Collection":
                    dictName = tag.get("localized_tag_name")
                    if (dictName in counting_things.keys()):
                        # print("Did incrementing on '" + dictName + "'")
                        counting_things[dictName] += howMany
                    else:
                        counting_things[dictName] = howMany
    # for item in items:
    #     is_crate = ("" != item.get("type"))
    #     x += 1
    #     print(is_crate)

    # "appid": 440,
    # "contextid": "2",
    # "assetid": "10773333633",
    # "classid": "4019192597",
    # "instanceid": "0",
    # "amount": "1"

    # "appid": 440,
    # "classid": "780650846",
    # "instanceid": "0",
    # "currency": 0,
    # "background_color": "3C352E",





    return counting_things

# Example usage with dummy data
cookies = load_cookies_from_file("secrets/cookies.txt")

user_id = '76561199190089345'  # Example SteamID64
app_id = 440  # Example App ID for CS:GO

inventory_data = get_inventory_with_cookies(user_id, app_id, cookies)
parsed_data = parse_items(inventory_data)
print(parsed_data)
# with open('JSON/output'+user_id+'.json', 'w') as file:
#     file.write(json.dumps(parsed_data))