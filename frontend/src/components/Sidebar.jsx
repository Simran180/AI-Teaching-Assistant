import { BookOpen, MessageSquare, Upload, BrainCircuit, Layers, Activity } from "lucide-react";
import styles from "./Sidebar.module.css";

const NAV = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "upload", label: "Upload", icon: Upload },
  { id: "quiz", label: "Quiz", icon: BrainCircuit },
  { id: "review", label: "Review", icon: Layers },
];

export default function Sidebar({ activeTab, onTabChange, health }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <BookOpen size={28} />
        <span>AI Teacher</span>
      </div>

      <nav className={styles.nav}>
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`${styles.navItem} ${activeTab === id ? styles.active : ""}`}
            onClick={() => onTabChange(id)}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className={styles.status}>
        <Activity size={14} />
        <span>
          {health
            ? `${health.total_chunks} chunks indexed`
            : "Connecting..."}
        </span>
      </div>
    </aside>
  );
}
