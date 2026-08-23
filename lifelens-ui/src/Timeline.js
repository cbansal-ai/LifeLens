import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

function Timeline({ userEmail }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchTimeline = async () => {
      setLoading(true);
      setError("");

      try {
        const params = new URLSearchParams();
        if (userEmail) params.set("account_email", userEmail);

        const response = await fetch(`${API_BASE}/timeline?${params.toString()}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load timeline.");
        setEvents(data);
      } catch (err) {
        setError(err.message || "Could not load timeline.");
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [userEmail]);

  return (
    <section className="timeline-page">
      <h1>Timeline</h1>
      <p className="timeline-subtitle">Important events saved for {userEmail}.</p>

      {loading ? (
        <div className="timeline-empty">Building your timeline...</div>
      ) : error ? (
        <div className="timeline-empty">{error}</div>
      ) : events.length === 0 ? (
        <div className="timeline-empty">No events found for this user.</div>
      ) : (
        <div className="timeline-list">
          {events.map((event, index) => (
            <article key={event.id || `${event.title}-${index}`} className="timeline-card">
              <h3>{event.title}</h3>
              <div className="timeline-meta">
                {event.event_type && <span>{event.event_type}</span>}
                {event.event_date && <span>{event.event_date}</span>}
                {event.company && <span>{event.company}</span>}
              </div>
              {event.summary && <p>{event.summary}</p>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default Timeline;
