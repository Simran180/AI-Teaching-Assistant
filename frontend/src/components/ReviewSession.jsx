import { useState, useEffect, useCallback, useRef } from "react";
import {
  Layers,
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { fetchDueReviews, submitReview } from "../services/api";
import styles from "./ReviewSession.module.css";

// Bloom's-taxonomy level → display label + accent color for the badge.
const BLOOM = {
  recall: { label: "Recall", color: "#60a5fa" },
  apply: { label: "Apply", color: "#a78bfa" },
  analyze: { label: "Analyze", color: "#f472b6" },
};

// FSRS ratings. The 1..4 values match the backend Rating enum exactly.
const RATINGS = [
  { value: 1, label: "Again", color: "var(--error)" },
  { value: 2, label: "Hard", color: "var(--warning)" },
  { value: 3, label: "Good", color: "var(--success)" },
  { value: 4, label: "Easy", color: "var(--accent)" },
];

// "in 3 days" / "in 5 hours" — friendly next-due label from an ISO timestamp.
function relativeDue(iso) {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "now";
  const mins = Math.round(ms / 60000);
  if (mins < 60) return `in ${mins} min`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `in ${hrs} hour${hrs > 1 ? "s" : ""}`;
  const days = Math.round(hrs / 24);
  return `in ${days} day${days > 1 ? "s" : ""}`;
}

export default function ReviewSession() {
  const [queue, setQueue] = useState([]); // items still to review this session
  const [current, setCurrent] = useState(null);
  const [counts, setCounts] = useState({ due_now: 0, due_today: 0 });
  const [reviewed, setReviewed] = useState(0); // done this session, for progress

  const [phase, setPhase] = useState("recall"); // "recall" | "revealed"
  const [userAnswer, setUserAnswer] = useState("");
  const [result, setResult] = useState(null); // submit response for the current card

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [exiting, setExiting] = useState(false); // drives the card-out animation

  const startedAt = useRef(Date.now()); // for response_time_ms

  const loadDue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchDueReviews("now", 50);
      setQueue(data.items);
      setCounts({ due_now: data.due_now, due_today: data.due_today });
      setCurrent(data.items[0] || null);
      setPhase("recall");
      setUserAnswer("");
      setResult(null);
      startedAt.current = Date.now();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDue();
  }, [loadDue]);

  async function handleRate(rating) {
    if (!current || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await submitReview({
        itemId: current.id,
        rating,
        userAnswer: userAnswer.trim() || undefined,
        responseTimeMs: Date.now() - startedAt.current,
      });
      setResult(res);
      setPhase("revealed");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleNext() {
    setExiting(true);
    // Let the card-out animation play before swapping in the next item.
    setTimeout(() => {
      const rest = queue.slice(1);
      setQueue(rest);
      setCurrent(rest[0] || null);
      setReviewed((n) => n + 1);
      setCounts((c) => ({ ...c, due_now: Math.max(0, c.due_now - 1) }));
      setPhase("recall");
      setUserAnswer("");
      setResult(null);
      startedAt.current = Date.now();
      setExiting(false);
    }, 220);
  }

  // Keyboard shortcuts: 1-4 to rate during recall, Enter/Space to advance.
  useEffect(() => {
    function onKey(e) {
      if (loading || submitting) return;
      if (phase === "recall" && ["1", "2", "3", "4"].includes(e.key)) {
        handleRate(Number(e.key));
      } else if (phase === "revealed" && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        handleNext();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, current, queue, loading, submitting, userAnswer]);

  // --- Render states ------------------------------------------------------

  if (loading) {
    return (
      <div className={styles.center}>
        <Loader2 size={32} className={styles.spinner} />
        <p>Loading your review queue…</p>
      </div>
    );
  }

  if (error && !current) {
    return (
      <div className={styles.center}>
        <p className={styles.error}>{error}</p>
        <button className={styles.retryBtn} onClick={loadDue}>
          Try again
        </button>
      </div>
    );
  }

  if (!current) {
    return (
      <div className={styles.center}>
        <div className={styles.allCaught}>
          <Sparkles size={40} />
          <h2>All caught up!</h2>
          {reviewed > 0 ? (
            <p>
              You reviewed <strong>{reviewed}</strong> card
              {reviewed > 1 ? "s" : ""} this session. Nice work.
            </p>
          ) : (
            <p>Nothing is due right now. Come back later, or upload material to generate new cards.</p>
          )}
          {counts.due_today > 0 && (
            <p className={styles.hint}>{counts.due_today} more due later today.</p>
          )}
        </div>
      </div>
    );
  }

  const bloom = BLOOM[current.bloom_level] || { label: current.bloom_level, color: "var(--accent)" };
  const remaining = counts.due_now;

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <div className={styles.header}>
          <Layers size={22} />
          <h2>Review</h2>
        </div>
        <span className={styles.remaining}>{remaining} due</span>
      </div>

      <div className={styles.cardWrap}>
        <div
          key={current.id}
          className={`${styles.card} ${exiting ? styles.cardExit : styles.cardEnter}`}
        >
          <div className={styles.cardMeta}>
            <span className={styles.bloomBadge} style={{ "--bloom": bloom.color }}>
              {bloom.label}
            </span>
            {current.topic && <span className={styles.topic}>{current.topic}</span>}
            <span className={styles.source}>{current.source}</span>
          </div>

          <p className={styles.question}>{current.question}</p>

          {phase === "recall" && (
            <>
              <textarea
                className={styles.answerInput}
                placeholder="Type your answer to get it graded (optional)…"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                rows={3}
                autoFocus
              />
              <p className={styles.prompt}>Recall the answer, then rate how well you knew it:</p>
              <div className={styles.ratings}>
                {RATINGS.map((r) => (
                  <button
                    key={r.value}
                    className={styles.rateBtn}
                    style={{ "--rate": r.color }}
                    onClick={() => handleRate(r.value)}
                    disabled={submitting}
                  >
                    <kbd>{r.value}</kbd>
                    {r.label}
                  </button>
                ))}
              </div>
              {submitting && (
                <p className={styles.submitting}>
                  <Loader2 size={14} className={styles.spinner} /> Grading…
                </p>
              )}
            </>
          )}

          {phase === "revealed" && result && (
            <div className={styles.reveal}>
              {result.grade && (
                <div
                  className={`${styles.verdict} ${
                    result.grade.is_correct ? styles.correct : styles.wrong
                  }`}
                >
                  {result.grade.is_correct ? (
                    <CheckCircle2 size={18} />
                  ) : (
                    <XCircle size={18} />
                  )}
                  {result.grade.is_correct ? "Correct" : "Not quite"}
                </div>
              )}

              <div className={styles.answerBlock}>
                <span className={styles.answerLabel}>Answer</span>
                <p>{result.expected_answer}</p>
              </div>

              {result.grade?.feedback && (
                <p className={styles.feedback}>{result.grade.feedback}</p>
              )}

              <div className={styles.nextRow}>
                <span className={styles.nextDue}>
                  Next review {relativeDue(result.next_due_at)}
                </span>
                <button className={styles.nextBtn} onClick={handleNext} autoFocus>
                  {queue.length > 1 ? "Next" : "Finish"}
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && current && <p className={styles.errorInline}>{error}</p>}
    </div>
  );
}
