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

def safe_date_to_iso(date_value):
    if hasattr(date_value, 'dt'):
        if isinstance(date_value.dt, datetime):
            return date_value.dt.isoformat()
        elif isinstance(date_value.dt, date):
            return date_value.dt.isoformat()
    return None

def create_or_update_notion_page(event):
    print(f"Processing event: {event.get('summary')}", flush=True)
    
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
        "UID": {"rich_text": [{"text": {"content": event.get('uid', '')}}]},
    }

    # Handle Date
    start_date = safe_date_to_iso(event.get('dtstart'))
    end_date = safe_date_to_iso(event.get('dtend'))
    if start_date:
        properties["Date"] = {
            "date": {
                "start": start_date,
                "end": end_date if end_date else None
            }
        }

    # Handle other properties
    if 'location' in event:
        properties["Location"] = {"rich_text": [{"text": {"content": str(event.get('location', ''))[:2000]}}]}
    
    if 'description' in event:
        properties["Description"] = {"rich_text": [{"text": {"content": str(event.get('description', ''))[:2000]}}]}

    # Handle Created date
    created_date = safe_date_to_iso(event.get('created'))
    if created_date:
        properties["Created"] = {"date": {"start": created_date}}

    # Handle Last Modified date
    last_modified_date = safe_date_to_iso(event.get('last-modified'))
    if last_modified_date:
        properties["Last Modified"] = {"date": {"start": last_modified_date}}

    # Only add Status if it's not empty
    status = event.get('status', '').strip()
    if status:
        properties["Status"] = {"select": {"name": status}}

    # Handle attendees
    if 'attendee' in event:
        attendees = event.get('attendee')
        if isinstance(attendees, list):
            attendees = ', '.join(str(a) for a in attendees)
        else:
            attendees = str(attendees)
        properties["Attendees"] = {"rich_text": [{"text": {"content": attendees[:2000]}}]}

    # Handle organizer
    if 'organizer' in event:
        properties["Organizer"] = {"rich_text": [{"text": {"content": str(event.get('organizer'))[:2000]}}]}

    # Handle URL
    if 'url' in event:
        properties["URL"] = {"url": str(event.get('url'))}

    print("Properties to be sent to Notion:", properties, flush=True)

    try:
        if query['results']:
            page_id = query['results'][0]['id']
            notion.pages.update(page_id=page_id, properties=properties)
            print(f"Updated event: {event.get('summary')}", flush=True)
        else:
            notion.pages.create(parent={"database_id": NOTION_DATABASE_ID}, properties=properties)
            print(f"Created new event: {event.get('summary')}", flush=True)
    except APIResponseError as e:
        print(f"Notion API error for event {event.get('summary')}: {str(e)}", flush=True)
        print(f"Problematic properties: {properties}", flush=True)

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
