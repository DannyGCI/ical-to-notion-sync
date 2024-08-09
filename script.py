import os
import sys
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
        "Date": {
            "date": {
                "start": event.get('dtstart').dt.isoformat(),
                "end": event.get('dtend').dt.isoformat() if 'dtend' in event else None
            }
        },
        "Location": {"rich_text": [{"text": {"content": event.get('location', '')}}]},
        "Description": {"rich_text": [{"text": {"content": event.get('description', '')[:2000]}}]},
        "Created": {"date": {"start": event.get('created').dt.isoformat() if 'created' in event else None}},
        "Last Modified": {"date": {"start": event.get('last-modified').dt.isoformat() if 'last-modified' in event else None}},
        "UID": {"rich_text": [{"text": {"content": event.get('uid', '')}}]},
        "Status": {"select": {"name": event.get('status', '')}},
    }

    # Handle attendees
    if 'attendee' in event:
        attendees = event.get('attendee')
        if isinstance(attendees, list):
            attendees = ', '.join(attendees)
        properties["Attendees"] = {"rich_text": [{"text": {"content": attendees[:2000]}}]}

    # Handle organizer
    if 'organizer' in event:
        properties["Organizer"] = {"rich_text": [{"text": {"content": str(event.get('organizer'))[:2000]}}]}

    # Handle URL
    if 'url' in event:
        properties["URL"] = {"url": event.get('url')}

    if query['results']:
        page_id = query['results'][0]['id']
        notion.pages.update(page_id=page_id, properties=properties)
        print(f"Updated event: {event.get('summary')}", flush=True)
    else:
        notion.pages.create(parent={"database_id": NOTION_DATABASE_ID}, properties=properties)
        print(f"Created new event: {event.get('summary')}", flush=True)

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
