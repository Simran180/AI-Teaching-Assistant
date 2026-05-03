import { useState, useRef } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Link,
  Youtube,
  Globe,
  FileAudio,
  FileVideo,
  Image,
} from "lucide-react";
import { uploadFile, ingestURL } from "../services/api";
import styles from "./UploadPanel.module.css";

const FILE_ACCEPT =
  ".pdf,.txt,.md,.docx,.mp3,.wav,.m4a,.ogg,.flac,.mp4,.mkv,.avi,.mov,.webm,.png,.jpg,.jpeg,.bmp,.tiff,.tif,.webp";

export default function UploadPanel({ onUploadComplete }) {
  const [topic, setTopic] = useState("General");
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const fileRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    setLoading(true);
    setStatus(null);

    try {
      const data = await uploadFile(file, topic);
      setStatus({
        type: "success",
        message: `"${data.filename}" processed (${data.source_type}) — ${data.chunks_created} chunks created.`,
      });
      onUploadComplete?.();
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function handleURLSubmit(e) {
    e.preventDefault();
    const url = urlInput.trim();
    if (!url || urlLoading) return;
    setUrlLoading(true);
    setStatus(null);

    try {
      const data = await ingestURL(url, topic);
      setStatus({
        type: "success",
        message: `${data.source_type} content ingested — ${data.chunks_created} chunks created.`,
      });
      setUrlInput("");
      onUploadComplete?.();
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setUrlLoading(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }

  const isLoading = loading || urlLoading;

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Ingest Learning Material</h2>
      <p className={styles.subtitle}>
        Upload files, paste YouTube links, or enter website URLs. Everything gets
        transcribed, chunked, and embedded for intelligent retrieval.
      </p>

      <div className={styles.topicRow}>
        <label className={styles.label}>Topic / Subject</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Deep Learning, Calculus, History..."
          className={styles.topicInput}
        />
      </div>

      {/* --- URL Ingestion --- */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Link size={18} /> From URL
        </h3>
        <form onSubmit={handleURLSubmit} className={styles.urlRow}>
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="Paste a YouTube link or website URL..."
            className={styles.urlInput}
            disabled={isLoading}
          />
          <button
            type="submit"
            className={styles.urlBtn}
            disabled={!urlInput.trim() || isLoading}
          >
            {urlLoading ? (
              <Loader2 size={18} className={styles.spinner} />
            ) : (
              "Ingest"
            )}
          </button>
        </form>
        <div className={styles.urlHints}>
          <span><Youtube size={14} /> YouTube videos</span>
          <span><Globe size={14} /> Any website / article</span>
        </div>
      </div>

      {/* --- File Upload --- */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Upload size={18} /> From File
        </h3>
        <div
          className={`${styles.dropzone} ${dragOver ? styles.dragOver : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            type="file"
            ref={fileRef}
            accept={FILE_ACCEPT}
            onChange={(e) => handleFile(e.target.files?.[0])}
            hidden
          />
          {loading ? (
            <>
              <Loader2 size={40} className={styles.spinner} />
              <p>Processing file...</p>
            </>
          ) : (
            <>
              <Upload size={36} />
              <p>Drag & drop a file here, or click to browse</p>
              <div className={styles.formatGrid}>
                <span><FileText size={14} /> PDF, TXT, MD, DOCX</span>
                <span><FileAudio size={14} /> MP3, WAV, M4A, OGG</span>
                <span><FileVideo size={14} /> MP4, MKV, AVI, MOV</span>
                <span><Image size={14} /> PNG, JPG, TIFF, WebP</span>
              </div>
              <span className={styles.hint}>Max 50 MB</span>
            </>
          )}
        </div>
      </div>

      {/* --- Status --- */}
      {status && (
        <div className={`${styles.alert} ${styles[status.type]}`}>
          {status.type === "success" ? (
            <CheckCircle2 size={18} />
          ) : (
            <AlertCircle size={18} />
          )}
          <span>{status.message}</span>
        </div>
      )}

      {/* --- How It Works --- */}
      <div className={styles.steps}>
        <h3>How it works</h3>
        <div className={styles.stepList}>
          <Step num="1" text="Upload a file or paste a URL (YouTube, website, PDF, audio, video, image)" />
          <Step num="2" text="Content is auto-detected, transcribed/extracted, and cleaned" />
          <Step num="3" text="Text is split into smart overlapping chunks" />
          <Step num="4" text="Each chunk is embedded as a vector and stored in FAISS" />
          <Step num="5" text="Ask questions in Chat — the AI retrieves the most relevant context" />
        </div>
      </div>
    </div>
  );
}

function Step({ num, text }) {
  return (
    <div className={styles.step}>
      <div className={styles.stepNum}>{num}</div>
      <span>{text}</span>
    </div>
  );
}
