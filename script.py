import os
import requests
from icalendar import Calendar
from notion_client import Client, APIResponseError
from datetime import datetime
import time
import hashlib

# Environment variables
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
ICAL_URL = os.environ.get("ICAL_URL")

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

def fetch_ical_data(url):
    response = requests.get(url)
    return response.text

def calculate_hash(data):
    return hashlib.md5(data.encode()).hexdigest()

def process_calendar(cal_data):
    cal = Calendar.from_ical(cal_data)
    for component in cal.walk():
        if component.name == "VEVENT":
            create_or_update_notion_page(component)

def create_or_update_notion_page(event):
    query = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "property": "Name",
            "title": {
                "equals": event.get('summary')
            }
        }
    )

    properties = {
        "Name": {"title": [{"text": {"content": event.get('summary')}}]},
        "Date": {"date": {"start": event.get('dtstart').dt.isoformat()}},
    }
    
    # Only add Description if it exists in the event
    if 'description' in event:
        properties["Notes"] = {"rich_text": [{"text": {"content": event.get('description', '')}}]}

    if query['results']:
        page_id = query['results'][0]['id']
        notion.pages.update(page_id=page_id, properties=properties)
        print(f"Updated event: {event.get('summary')}")
    else:
        notion.pages.create(parent={"database_id": NOTION_DATABASE_ID}, properties=properties)
        print(f"Created new event: {event.get('summary')}")

def main():
    last_hash = None
    while True:
        try:
            print(f"Checking for changes at {datetime.now()}")
            cal_data = fetch_ical_data(ICAL_URL)
            current_hash = calculate_hash(cal_data)
            
            if current_hash != last_hash:
                print("Changes detected, processing updates...")
                process_calendar(cal_data)
                last_hash = current_hash
            else:
                print("No changes detected")
            
            # Wait for a short time before checking again
            time.sleep(10)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}")
        except APIResponseError as e:
            print(f"Notion API error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
        
        # Wait before retrying after an error
        time.sleep(60)

if __name__ == "__main__":
    main()
