import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import UploadPanel from "./components/UploadPanel";
import QuizPanel from "./components/QuizPanel";
import { healthCheck, fetchTopics } from "./services/api";

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
  const [activeTab, setActiveTab] = useState("chat");
  const [health, setHealth] = useState(null);
  const [topics, setTopics] = useState([]);

  const refreshData = useCallback(async () => {
    try {
      const [h, t] = await Promise.all([healthCheck(), fetchTopics()]);
      setHealth(h);
      setTopics(t.topics || []);
    } catch {
      /* backend may not be running yet */
    }
  }, []);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  return (
    <div style={appStyles}>
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} health={health} />
      <main style={mainStyles}>
        {activeTab === "chat" && <ChatPanel topics={topics} />}
        {activeTab === "upload" && <UploadPanel onUploadComplete={refreshData} />}
        {activeTab === "quiz" && <QuizPanel topics={topics} />}
      </main>
    </div>
  );
}
