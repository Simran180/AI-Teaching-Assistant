const BASE = import.meta.env.VITE_API_URL || "/api";

export async function sendChat(question, topic, mode) {
  const res = await fetch(`${BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, topic: topic || null, mode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Chat request failed");
  }
  return res.json();
}

export async function uploadFile(file, topic) {
  const form = new FormData();
  form.append("file", file);
  form.append("topic", topic || "General");

  const res = await fetch(`${BASE}/upload/`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function ingestURL(url, topic) {
  const res = await fetch(`${BASE}/ingest/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, topic: topic || "General" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "URL ingestion failed");
  }
  return res.json();
}

export async function generateQuiz(topic, numQuestions, difficulty) {
  const res = await fetch(`${BASE}/quiz/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topic,
      num_questions: numQuestions,
      difficulty,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Quiz generation failed");
  }
  return res.json();
}

export async function fetchTopics() {
  const res = await fetch(`${BASE}/topics/`);
  if (!res.ok) throw new Error("Failed to fetch topics");
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}
