from flask import Flask, Response
from notion_client import Client
from icalendar import Calendar, Event
from datetime import datetime
import os

app = Flask(__name__)

# Initialize Notion client
notion = Client(auth=os.environ["NOTION_API_KEY"])
database_id = os.environ["NOTION_DATABASE_ID"]

def fetch_notion_events():
    results = notion.databases.query(database_id=database_id).get("results")
    events = []
    for page in results:
        properties = page["properties"]
        event = {
            "title": properties["Name"]["title"][0]["text"]["content"],
            "start": properties["Date"]["date"]["start"],
            "end": properties["Date"]["date"].get("end"),
        }
        events.append(event)
    return events

def create_ical(events):
    cal = Calendar()
    for event in events:
        ical_event = Event()
        ical_event.add("summary", event["title"])
        ical_event.add("dtstart", datetime.fromisoformat(event["start"]))
        if event["end"]:
            ical_event.add("dtend", datetime.fromisoformat(event["end"]))
        cal.add_component(ical_event)
    return cal.to_ical()

@app.route("/calendar.ics")
def serve_calendar():
    events = fetch_notion_events()
    ical_data = create_ical(events)
    return Response(ical_data, mimetype="text/calendar")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000))
