import { useState } from "react";
import "./App.css";
import Timeline from "./Timeline";

function App() {
  const [page, setPage] = useState("home");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const askQuestion = async () => 
    {
      if (!question.trim()) {
  setMessages((prevMessages) => [
    ...prevMessages,
    {
      sender: "ai",
      text: "Please enter a question."
    }
  ]);
  return;
    }

      const userMessage = 
      {
      sender: "user",
      text: question,
      };

    setMessages((prevMessages) => [...prevMessages, userMessage]);

    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessages((prevMessages) => [
          ...prevMessages,
        {
        sender: "ai",
        text: data.detail,
        },
  ]);

  setLoading(false);
  return;
}

      const aiMessage = {
        sender: "ai",
        text: data.answer,
      };

      setMessages((prevMessages) => [...prevMessages, aiMessage]);
    } 
    catch (error) {
      console.error(error);

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "ai",
          text: "Something went wrong.",
        },
      ]);
    }

    setQuestion("");
    setLoading(false);
  };  

  return (
    <div className="container">
      <h1>LifeLens</h1>

      <div className="nav-buttons">
        
        <button onClick={() => setPage("home")}>Home</button>
        <button onClick={() => setPage("timeline")}>Timeline</button>
      </div>

      {page === "home" && (
        <>
          <div className="chat-box">
            {messages.map((message, index) => (
              <div
                key={index}
                className={
                  message.sender === "user"
                    ? "message user-message"
                    : "message ai-message"
                }
              >
                <strong>
                  {message.sender === "user" ? "You" : "LifeLens"}:
                </strong>{" "}
                {message.text}
              </div>
            ))}

            {loading && (
              <div className="message ai-message">
                <strong>LifeLens:</strong> 🤖 Thinking...
              </div>
            )}
          </div>

          <div className="input-section">
            <input
              type="text"
              placeholder="Ask me anything about your life..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />

            <button onClick={askQuestion}>Ask</button>
          </div>
        </>
      )}

      {page === "timeline" && <Timeline />}
    </div>
  );
}

export default App;
