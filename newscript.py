import requests
import json
import time
import csv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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

def get_inventory_with_cookies(user_id, app_id, cookies, retry_max):
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

    if retry_max:
        failures = -99

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

def price_querier(driver,item_data):
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
            zack_sleep(180)
            return price_querier(url)

        # if we got here, we have a price that should be able to load on this item

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

def price_querier_selenium(driver,item_data):
    
    if item_data[0] == "Mann%20Co.%20Stockpile%20Crate":
        return (0.03,True)

    marketable = item_data[1]
    if marketable == False:
        # 0 means its in the non marketable list
        return (0,False)
    url = f"https://steamcommunity.com/market/listings/440/"
    url = url + item_data[0]

    # this should be set to max int or something if we are doing a real run maybe ?
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        driver.get(url)

        time.sleep(1)
        page_source = driver.page_source

        if "An error was encountered while processing your request:" in page_source:
            print("Rate limit detected, waiting 180s...")
            time.sleep(180)
            retry_count += 1
            continue
        elif "There was an error getting listings for this item. Please try again later." in page_source:
            print("Steam backend crapped the bed, waiting 5s...")
            time.sleep(5)
            retry_count += 1
            continue
        elif "There are no listings for this item." in page_source:
            print("Item not found, non-marketable or bad name: \"" + item_data[0] + "\"")
            with open("JSON/badItems.txt", 'a') as file:
                file.write(url + " failed with bad item name.\n")
            return(-1.0,False)

        time.sleep(4)
        try:
            forsale_div = driver.find_element(By.ID, "market_commodity_forsale")

            price_spans = forsale_div.find_elements(By.CLASS_NAME, "market_commodity_orders_header_promote")

            for span in price_spans:
                if '$' in span.text:
                    price_text = span.text.strip().replace('$','').strip()
                    print("Price found: " + price_text)
                    return (float(price_text),True)
            print("Should not get here, maybe price didn't load?")
            return (-2,False)
        except Exception as e:
            print(f"Error finding price element: {str(e)}")
            retry_count += 1
            time.sleep(5)

    
    # Failed after multiple retries
    return (-4,False)

def nameify(key):
    marketable = True
    if any(x in key.lower() for x in ["crate","cooler","reel"]):
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("#","%23")
    elif "cosmetics" in key.lower():
        item_name = '%20'.join(key.split())
        item_name = item_name.replace("Cosmetics%20Collection","Cosmetic%20Case")
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

    item_name = item_name.replace("#","%23")
    return (item_name,marketable)

def add_price_of(driver,key):
    item_data = nameify(key)
    querier_output = price_querier_selenium(driver,item_data)
    # add (name: [price, marketable]) to dict
    global prices
    prices[key] = querier_output

def find_prices(driver,key):
    global prices
    if key not in prices.keys():
        add_price_of(driver,key)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.binary_location = "D:\chromium\chrome-win\chrome.exe"

    # Set path to chromedriver
    # VINCENT ADJUST
    service = Service(executable_path="D:\chromium\chromedriver_win32\chromedriver.exe")

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def dump_prices(priceFileName):
    global prices

    with open(priceFileName, 'w') as file:
        file.write(json.dumps(prices))

def print_that_result(total_values,generic_filename):

    json_filename = "JSON/final/data/" + generic_filename
    text_filename = "JSON/final/text/" + generic_filename

    # Write to JSON file
    with open(json_filename, 'w') as json_file:
        json.dump(total_values, json_file, indent=4)

    # Write to text file with pretty output
    with open(text_filename, 'w') as text_file:
        for crate_name, total_value in total_values.items():
            if crate_name != 'Total Value':
                text_file.write(f"{crate_name}: ${total_value:.2f}\n")
        text_file.write(f"Total Value of all crates: ${total_values['Total Value']:.2f}\n")


def build_output(data,generic_filename):
    # TODO just multiply prices by number of the item, make the output vincent needed.
    print("Not done yet... this just will build the output to the format vicncent wants")
    global prices
    total_values = {}
    combined_total = 0
    for crate_name, count in data.items():
        if crate_name in prices and prices[crate_name][1]:
            price = prices[crate_name][0]
            total_value = count * price
            total_values[crate_name] = total_value
            combined_total += total_value
    total_values['Total Value'] = combined_total

    print_that_result(total_values,generic_filename)
    print("Done :)")

# 440 is CSGO
app_id = 440

# if this stops working randomly put new cookies in the cookie jar
cookies = load_cookies_from_file("secrets/cookies.txt")


def read_json_files_and_sum_total_values(directory):
    total_value = 0

    # Get all files in the specified directory
    all_files = os.listdir(directory)
    
    # Filter out only the .json files
    json_files = [f for f in all_files if f.endswith('.json')]

    for json_file in json_files:
        file_path = os.path.join(directory, json_file)
        with open(file_path, 'r') as file:
            data = json.load(file)
            if "Total Value" in data:
                total_value += data["Total Value"]
    
    return total_value

def write_output_to_file(output_file, total_value, item_tallies):
    output_data = {"Total Value": total_value}

    with open(output_file, 'w') as file:
        json.dump(output_data, file, indent=4)


# This is the driver for this script
def read_inventory(user_id,retry_max):
    global app_id
    global cookies

    all_files = os.listdir("JSON/counted")
    
    # Filter out only the .json files and remove the .json extension
    json_files = [f[:-5] for f in all_files if f.endswith('.json')]

    countFileName = ""

    nameOutput = get_steam_person_name(user_id,cookies,"profiles")

    if (nameOutput in json_files):
        print(nameOutput + " was already counted, skipping...\n")
        return
    
    if "BREWSKI-CASEGOD-" in (nameOutput.strip().upper()):
        countFileName = "JSON/counted/Brewski425.json"
    else:
        countFileName = "JSON/counted/" + nameOutput + ".json"


    generic_filename = countFileName[len("JSON/counted/"):]

    # If it's cached already
    if (os.path.isfile(countFileName)):
        with open(countFileName, 'r') as file:
            json_data = file.read()
            parsed_data = json.loads(json_data)
    # If we haven't run it for this acc
    else:

        # TODO cache everything, less runtime every time i am debugging

        # Loading up some inventory here
        inventory_data = get_inventory_with_cookies(user_id, app_id, cookies, retry_max)
        if type(inventory_data) == str and inventory_data == "Error, too many bad requests":
            with open("JSON/errorLog.txt", 'a') as file:
                file.write(user_id + " failed.\n")
            return
        parsed_data = parse_items(inventory_data)
        

        print(nameOutput.strip() + " succeeded!! Outputting to " + countFileName[13:])

        with open(countFileName, 'w') as file:
            file.write(json.dumps(parsed_data))

    
    priceFileName = "JSON/priced/Brewski425.json"
        

    # Start up selenium
    driver = setup_driver()


    if (os.path.isfile(priceFileName)):
        
        with open(priceFileName, 'r') as file:
            json_data = file.read()
            global prices
            data = json.loads(json_data)
            prices = {name: value for name, value in data.items() if value[1] is not False}
        for key in parsed_data.keys():
            find_prices(driver,key)
        dump_prices(priceFileName)
        
    else:

        # Price searching
        for key in parsed_data.keys():
            find_prices(driver,key)

        dump_prices(priceFileName)

    driver.quit()
    return build_output(parsed_data,generic_filename)
    
    return


def main():
    print("\n")
    # Clear badItems file
    with open("JSON/badItems.txt", 'w') as file:
        file.write("\n")


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
    #     read_inventory(user, False)
    # read_inventory("76561199125110580",True)


    # read_inventory(users[0]) # succeeds, already cached
    # read_inventory(users[1]) # fails
    # read_inventory(users[5]) # should succeed?
    # print(prices)
    directory_path = 'JSON/final/data'
    output_file = 'JSON/final/tally.json'

    total_value = read_json_files_and_sum_total_values(directory_path)
    write_output_to_file(output_file, total_value)
    print(total_value)

if __name__ == "__main__":
    main()