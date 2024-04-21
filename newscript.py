import requests
import json
import time
import csv
from bs4 import BeautifulSoup

assets = []
prices = dict()

def load_cookies_from_file(filepath):
    """
    Load cookies from a given JSON file.
    
    :param filepath: Path to the JSON file containing cookies.
    :return: A dictionary of cookies.
    """
    with open(filepath, 'r') as file:
        cookies = json.load(file)
    return cookies

def get_steam_person_name(user_id, cookies, uri_element):
    url = f"https://steamcommunity.com/{uri_element}/{user_id}"
    headers = {'Cookie': '; '.join([f'{key}={value}' for key, value in cookies.items()])}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        persona_name_tag = soup.find('span', class_='actual_persona_name')

        if persona_name_tag:
            return persona_name_tag.text
        else:
            if uri_element != "id":
                return get_steam_person_name(user_id, cookies, "id")
            return "Persona name not findable."

        return persona_name_tag.text if persona_name_tag else "Persona name not findable."
    else:
        return "Failed to retrieve profile, response code: " + str(response.status_code)

def zack_sleep(duration):
    time.sleep(duration)
    return

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
    succeeded_once = False

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
            succeeded_once = True
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
            if (failures >= 4) and succeeded_once == False:
                return "Error, too many bad requests"
            failures += 1
        first_run = False
        if succeeded_once:
            zack_sleep(0.5)
        else:
            zack_sleep(0.3)
    
    
    return items

def is_unique(new_dict, dict_list):
    for existing_dict in dict_list:
        if existing_dict == new_dict:
            return False
    return True

def count_occurrences(i_id, c_id):
    number_of_occurrences = 0
    for asset in assets:
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
    return counting_things

def price_querier(item_data):
    marketable = item_data[1]
    if marketable == False:
        # 0 means its in the non marketable list
        return (0,False)
    url = f"https://steamcommunity.com/market/listings/440/"
    url = url + item_data[0]
    
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Is the item name valid??
        error_message_span = soup.find('div', class_='market_listing_table_message')
        if error_message_span and "There are no listings for this item." in error_message_span.text:
            print('Bad item name! Printed to badItems.txt')
            zack_sleep(0.5)
            with open("JSON/badItems.txt", 'a') as file:
                file.write(url + " failed with bad item name.\n")
            # -1 means it had bad name on query
            return (-1,False)

        # Is the steam backend shit??
        if error_message_span and "There was an error getting listings for this item. Please try again later." in error_message_span.text:
            print('Steam backend is poop, sleeping 3s...')
            zack_sleep(3)
            return price_querier(url)

        # Did we get rate limited (time for big sleep)
        rate_limit_p = soup.find('p', class_='sectionText')
        if rate_limit_p and "An error was encountered while processing your request:" in rate_limit_p.text:
            print('Rate limited, sleeping 30s...')
            zack_sleep(30)
            return price_querier(url)

        # If we got here i am *praying* that we are on the price screen
        buy_price_div = soup.find(id="market_commodity_forsale")

        #DEBUG
        print(buy_price_div)
        zack_sleep(4)
        print("slept.. IN DEBUG MODE")

        if buy_price_div:
            price_span = buy_price_div.find('span', class_='market_commodity_orders_header_promote', string=lambda text: text and '$' in text)

            if price_span:
                price = price_span.text[1:]
            else:
                #TODO this is always where we go right now, because we dont have javascript running. see gpt chat for selenium tutorial..
                print("why is it missing???")
                # -2 means price missing
                price = -2
                marketable = False
        else:
            print("WTF happened???")
            # -3 means something crazy goin on
            return (-3,False)
        
        return (price,marketable)

def nameify(key):
    marketable = True
    if any(x in key.lower() for x in ["crate","cooler","reel"]):
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("#","%23")
    elif "cosmetics" in key.lower():
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("Cosmetics","Cosmetic%20Case")
    elif any(x in key.lower() for x in ["scream fortress","winter","infernal reward","jungle jackpot","summer"]):
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("Collection","War%20Paint%20Case")
        # Scream%20Fortress%20Collection
    elif any(x in key.lower() for x in ["decorated war hero","contract campaigner"]):
        item_name = ""
        marketable = False
        # Scream%20Fortress%20Collection
    else:
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("Collection","Case")
    return (item_name,marketable)

def add_price_of(key):
    item_data = nameify(key)
    querier_output = price_querier(item_data)
    # add (name: [price, marketable]) to dict
    global prices
    prices[key] = querier_output

def find_prices(key):
    global prices
    if key not in prices.keys():
        add_price_of(key)

def build_output(data):
    print("Not done yet... this just will build the output to the format vicncent wants")

# 440 is CSGO
app_id = 440

# if this stops working randomly put new cookies in the cookie jar
cookies = load_cookies_from_file("secrets/cookies.txt")

def read_inventory(user_id):
    global app_id
    global cookies

    fileName = ""

    inventory_data = get_inventory_with_cookies(user_id, app_id, cookies)
    if type(inventory_data) == str and inventory_data == "Error, too many bad requests":
        with open("JSON/errorLog.txt", 'a') as file:
            file.write(user_id + " failed.\n")
        return
    parsed_data = parse_items(inventory_data)
    nameOutput = get_steam_person_name(user_id,cookies,"profiles")
    
    if "BREWSKI-CASEGOD-" in (nameOutput.strip().upper()):
        fileName = "JSON/counted/Brewski425.json"
    else:
        fileName = "JSON/counted/" + nameOutput + ".json"

    print(nameOutput.strip() + " succeeded!! Outputting to " + fileName[13:])

    with open(fileName, 'w') as file:
        file.write(json.dumps(parsed_data))

    for key in parsed_data.keys():
        find_prices(key)

    #TODO make sure something is done with the built output
    #TODO write this function
    return build_output(parsed_data)
    
    return

with open('secrets/userIds.txt') as file:
    csvreader = csv.reader(file)
    users = next(csvreader)

# Clearing error log
with open("JSON/errorLog.txt", 'w') as file:
    file.write("Error log:\n\n")

# Clearing bad item log
with open("JSON/badItems.txt", 'w') as file:
    file.write("Bad item log:\n\n")
# user_id = '76561198878832586'  # Example SteamID64

#This is how we will run the stuff
# for user in users:
#     read_inventory(user)

#This is debug mode stuff for testing why the hell the webpage wasn't coming with the price
read_inventory(users[0])
print(prices)