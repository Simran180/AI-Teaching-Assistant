import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import UploadPanel from "./components/UploadPanel";
import QuizPanel from "./components/QuizPanel";
import ReviewSession from "./components/ReviewSession";
import Dashboard from "./components/Dashboard";
import { healthCheck, fetchTopics, fetchReviewStats } from "./services/api";

const appStyles = {
  display: "flex",
  height: "100vh",
  overflow: "hidden",
};

const mainStyles = {
  flex: 1,
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [topics, setTopics] = useState([]);
  // Bumped after uploads/reviews so Dashboard refetches when it remounts.
  const [statsVersion, setStatsVersion] = useState(0);
  const didInitTab = useRef(false);

  const refreshData = useCallback(async () => {
    try {
      const [h, t] = await Promise.all([healthCheck(), fetchTopics()]);
      setHealth(h);
      setTopics(t.topics || []);
      setStatsVersion((v) => v + 1);
    } catch {
      /* backend may not be running yet */
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Landing tab: dashboard when the user already has review cards, else chat.
  // Runs once, and never overrides a tab the user has already chosen.
  useEffect(() => {
    if (didInitTab.current) return;
    fetchReviewStats()
      .then((stats) => {
        didInitTab.current = true;
        if ((stats.total_items || 0) === 0) setActiveTab("chat");
      })
      .catch(() => {
        didInitTab.current = true;
        setActiveTab("chat");
      });
  }, []);

  return (
    <div style={appStyles}>
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} health={health} />
      <main style={mainStyles}>
        {activeTab === "dashboard" && (
          <Dashboard
            key={statsVersion}
            onStartReview={() => setActiveTab("review")}
            onGoUpload={() => setActiveTab("upload")}
          />
        )}
        {activeTab === "chat" && <ChatPanel topics={topics} />}
        {activeTab === "upload" && <UploadPanel onUploadComplete={refreshData} />}
        {activeTab === "quiz" && <QuizPanel topics={topics} />}
        {activeTab === "review" && <ReviewSession />}
      </main>
    </div>
  );
}
