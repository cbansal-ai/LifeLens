import { useEffect, useState } from "react";

function Timeline() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetchTimeline();
  }, []);

  const fetchTimeline = async () => {
    const response = await fetch("http://127.0.0.1:8000/timeline");
    const data = await response.json();

    setEvents(data);
  };

  return (
    <div className="timeline">
      <h2>Timeline</h2>

      {events.length === 0 ? (
        <p>No events found.</p>
      ) : (
        events.map((event) => (
          <div key={event.id} className="timeline-card">
            <h3>{event.title}</h3>

            <p>
              <strong>Type:</strong> {event.event_type}
            </p>

            <p>
              <strong>Date:</strong> {event.event_date}
            </p>

            <p>{event.summary}</p>
          </div>
        ))
      )}
    </div>
  );
}

export default Timeline;