import { useState, useEffect, useCallback } from "react";
import {
  LayoutDashboard,
  Clock,
  CalendarDays,
  Layers,
  Flame,
  TrendingUp,
  ArrowRight,
  Upload,
  Loader2,
} from "lucide-react";
import { fetchReviewStats } from "../services/api";
import styles from "./Dashboard.module.css";

const CARDS = [
  { key: "due_now", label: "Due now", icon: Clock, accent: "var(--warning)" },
  { key: "due_today", label: "Due today", icon: CalendarDays, accent: "var(--accent)" },
  { key: "total_items", label: "Total cards", icon: Layers, accent: "var(--success)" },
  { key: "streak_days", label: "Day streak", icon: Flame, accent: "#fb923c" },
];

export default function Dashboard({ onStartReview, onGoUpload }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setStats(await fetchReviewStats());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className={styles.center}>
        <Loader2 size={32} className={styles.spinner} />
        <p>Loading your dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.center}>
        <p className={styles.error}>{error}</p>
        <button className={styles.primaryBtn} onClick={load}>Try again</button>
      </div>
    );
  }

  if (!stats || stats.total_items === 0) {
    return (
      <div className={styles.center}>
        <LayoutDashboard size={40} className={styles.muted} />
        <h2>No review cards yet</h2>
        <p className={styles.subtitle}>
          Upload material and we'll automatically turn it into spaced-repetition cards.
        </p>
        <button className={styles.primaryBtn} onClick={onGoUpload}>
          <Upload size={16} /> Upload material
        </button>
      </div>
    );
  }

  const maxStability = Math.max(
    1,
    ...stats.mastery_by_topic.map((t) => t.avg_stability || 0)
  );

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <div className={styles.header}>
          <LayoutDashboard size={24} />
          <h2>Dashboard</h2>
        </div>
        {stats.due_now > 0 && (
          <button className={styles.primaryBtn} onClick={onStartReview}>
            Start review ({stats.due_now}) <ArrowRight size={16} />
          </button>
        )}
      </div>

      <div className={styles.cards}>
        {CARDS.map(({ key, label, icon: Icon, accent }) => (
          <div key={key} className={styles.card} style={{ "--accent-card": accent }}>
            <div className={styles.cardIcon}>
              <Icon size={20} />
            </div>
            <div className={styles.cardValue}>{stats[key]}</div>
            <div className={styles.cardLabel}>{label}</div>
          </div>
        ))}
      </div>

      <div className={styles.chartCard}>
        <div className={styles.chartHeader}>
          <TrendingUp size={18} />
          <h3>Mastery by topic</h3>
        </div>
        <p className={styles.chartCaption}>
          Average memory strength per topic — longer bars mean better-retained material.
        </p>

        {stats.mastery_by_topic.length === 0 ? (
          <p className={styles.muted}>No topics with review history yet.</p>
        ) : (
          <div className={styles.bars}>
            {stats.mastery_by_topic.map((t) => {
              const pct = Math.round(((t.avg_stability || 0) / maxStability) * 100);
              return (
                <div key={t.topic} className={styles.barRow}>
                  <span className={styles.barLabel} title={t.topic}>
                    {t.topic}
                    <span className={styles.barCount}>{t.item_count}</span>
                  </span>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{ width: `${Math.max(pct, 4)}%` }}
                    />
                  </div>
                  <span className={styles.barValue}>
                    {t.avg_stability != null ? `${t.avg_stability.toFixed(1)}d` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
