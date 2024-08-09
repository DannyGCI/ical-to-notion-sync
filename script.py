import os
import sys
import requests
from icalendar import Calendar
from notion_client import Client, APIResponseError
from datetime import datetime, date, timedelta
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

def safe_date_to_iso(date_value):
    if hasattr(date_value, 'dt'):
        if isinstance(date_value.dt, datetime):
            return date_value.dt.isoformat()
        elif isinstance(date_value.dt, date):
            return date_value.dt.isoformat()
    return None

def fetch_notion_events():
    events = []
    has_more = True
    start_cursor = None
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
    
    while has_more:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            start_cursor=start_cursor,
            filter={
                "property": "Date",
                "date": {
                    "on_or_after": one_day_ago
                }
            }
        )
        events.extend(response['results'])
        has_more = response['has_more']
        start_cursor = response['next_cursor']
    return events

def delete_notion_page(page_id):
    try:
        notion.pages.update(page_id=page_id, archived=True)
        print(f"Deleted event with ID: {page_id}", flush=True)
    except APIResponseError as e:
        print(f"Error deleting Notion page {page_id}: {str(e)}", flush=True)

def process_calendar(cal_data):
    cal = Calendar.from_ical(cal_data)
    ical_events = set()
    one_day_ago = datetime.now() - timedelta(days=1)
    
    for component in cal.walk():
        if component.name == "VEVENT":
            event_date = component.get('dtstart').dt
            if isinstance(event_date, date):
                event_date = datetime.combine(event_date, datetime.min.time())
            
            if event_date >= one_day_ago:
                ical_events.add(component.get('uid'))
                create_or_update_notion_page(component)
    
    notion_events = fetch_notion_events()
    for event in notion_events:
        notion_uid = event['properties']['UID']['rich_text'][0]['plain_text'] if event['properties']['UID']['rich_text'] else None
        if notion_uid and notion_uid not in ical_events:
            delete_notion_page(event['id'])

def create_or_update_notion_page(event):
    # ... (rest of the function remains the same)
    pass  # Remove this line when you uncomment the function body

def main():
    last_hash = None
    while True:
        try:
            print(f"Checking for changes at {datetime.now()}", flush=True)
            cal_data = fetch_ical_data(ICAL_URL)
            current_hash = calculate_hash(cal_data)
            
            if current_hash != last_hash:
                print("Changes detected, processing updates...", flush=True)
                process_calendar(cal_data)
                last_hash = current_hash
            else:
                print("No changes detected", flush=True)
            
            # Wait for a short time before checking again
            time.sleep(10)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {str(e)}", flush=True)
        except APIResponseError as e:
            print(f"Notion API error: {str(e)}", flush=True)
        except Exception as e:
            print(f"Unexpected error: {str(e)}", flush=True)
        
        # Wait before retrying after an error
        time.sleep(60)

if __name__ == "__main__":
    print("Script started", flush=True)
    main()
