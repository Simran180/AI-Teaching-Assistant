import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { sendChat } from "../services/api";
import styles from "./ChatPanel.module.css";

const MODES = [
  { value: "eli5", label: "ELI5" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

export default function ChatPanel({ topics }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your AI Teaching Assistant. Upload some learning material, then ask me anything about it. I'll explain concepts, answer questions, and help you learn.",
    },
  ]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("intermediate");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const data = await sendChat(q, topic, mode);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className={styles.select}
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>

        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className={styles.select}
        >
          <option value="">All Topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.messages}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${styles.message} ${
              msg.role === "user" ? styles.user : styles.assistant
            }`}
          >
            <div className={styles.avatar}>
              {msg.role === "user" ? <User size={18} /> : <Sparkles size={18} />}
            </div>
            <div className={styles.bubble}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
              {msg.sources?.length > 0 && (
                <div className={styles.sources}>
                  {msg.sources.map((s, j) => (
                    <span key={j} className={styles.sourceTag}>
                      {s.source}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className={`${styles.message} ${styles.assistant}`}>
            <div className={styles.avatar}>
              <Sparkles size={18} />
            </div>
            <div className={styles.bubble}>
              <Loader2 size={20} className={styles.spinner} />
              <span className={styles.thinking}>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className={styles.inputBar} onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your material..."
          className={styles.input}
          disabled={loading}
        />
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={!input.trim() || loading}
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
}
