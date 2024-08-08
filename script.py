import os
import requests
from icalendar import Calendar
from notion_client import Client
from datetime import datetime
import time

# Environment variables
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
ICAL_URL = os.environ.get("ICAL_URL")

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

def fetch_ical_data(url):
    response = requests.get(url)
    return Calendar.from_ical(response.text)

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

    if query['results']:
        page_id = query['results'][0]['id']
        notion.pages.update(
            page_id=page_id,
            properties={
                "Date": {"date": {"start": event.get('dtstart').dt.isoformat()}},
                "Description": {"rich_text": [{"text": {"content": event.get('description', '')}}]}
            }
        )
        print(f"Updated event: {event.get('summary')}")
    else:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": event.get('summary')}}]},
                "Date": {"date": {"start": event.get('dtstart').dt.isoformat()}},
                "Description": {"rich_text": [{"text": {"content": event.get('description', '')}}]}
            }
        )
        print(f"Created new event: {event.get('summary')}")

def main():
    last_sync_time = None
    while True:
        current_time = datetime.now()
        print(f"Starting sync at {current_time}")
        
        try:
            cal = fetch_ical_data(ICAL_URL)
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    # Only process events that have been updated since the last sync
                    last_modified = component.get('last-modified', component.get('dtstamp'))
                    if last_sync_time is None or last_modified.dt > last_sync_time:
                        create_or_update_notion_page(component)
            
            last_sync_time = current_time
            print(f"Sync completed at {datetime.now()}")
        except requests.exceptions.RequestException as e:
            print(f"Network error during sync: {str(e)}")
        except notion_client.errors.APIResponseError as e:
            print(f"Notion API error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error during sync: {str(e)}")
        
        time.sleep(3)  # Wait for 3 seconds before the next sync

if __name__ == "__main__":
    main()
