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

// --- Spaced-repetition review -------------------------------------------

export async function fetchDueReviews(scope = "now", limit = 50) {
  const res = await fetch(`${BASE}/review/due?scope=${scope}&limit=${limit}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch due reviews");
  }
  return res.json();
}

export async function submitReview({ itemId, rating, userAnswer, responseTimeMs }) {
  const res = await fetch(`${BASE}/review/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_id: itemId,
      rating,
      user_answer: userAnswer || null,
      response_time_ms: responseTimeMs ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit review");
  }
  return res.json();
}

export async function fetchReviewStats() {
  const res = await fetch(`${BASE}/review/stats`);
  if (!res.ok) throw new Error("Failed to fetch review stats");
  return res.json();
}

export async function seedReview({ source, topic, maxChunks = 5 }) {
  const res = await fetch(`${BASE}/review/seed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source: source || null,
      topic: topic || null,
      max_chunks: maxChunks,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to seed review items");
  }
  return res.json();
}
