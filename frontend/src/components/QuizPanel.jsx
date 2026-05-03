import { useState } from "react";
import { BrainCircuit, CheckCircle2, XCircle, Loader2, RotateCcw } from "lucide-react";
import { generateQuiz } from "../services/api";
import styles from "./QuizPanel.module.css";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"];

export default function QuizPanel({ topics }) {
  const [topic, setTopic] = useState("");
  const [numQ, setNumQ] = useState(5);
  const [difficulty, setDifficulty] = useState("intermediate");
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate(e) {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    setQuiz(null);
    setAnswers({});
    setShowResults(false);

    try {
      const data = await generateQuiz(topic, numQ, difficulty);
      setQuiz(data.questions);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function selectAnswer(qIdx, option) {
    if (showResults) return;
    setAnswers((prev) => ({ ...prev, [qIdx]: option }));
  }

  function handleSubmit() {
    setShowResults(true);
  }

  function handleReset() {
    setQuiz(null);
    setAnswers({});
    setShowResults(false);
  }

  const score = quiz
    ? quiz.filter((q, i) => answers[i] === q.correct_answer).length
    : 0;

  return (
    <div className={styles.container}>
      {!quiz ? (
        <div className={styles.setup}>
          <div className={styles.header}>
            <BrainCircuit size={32} />
            <h2>Quiz Generator</h2>
          </div>
          <p className={styles.subtitle}>
            Generate quizzes from your uploaded material to test your understanding.
          </p>

          <form onSubmit={handleGenerate} className={styles.form}>
            <div className={styles.field}>
              <label>Topic</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Neural Networks, Calculus..."
                list="topic-suggestions"
              />
              <datalist id="topic-suggestions">
                {topics.map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </div>

            <div className={styles.row}>
              <div className={styles.field}>
                <label>Questions</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={numQ}
                  onChange={(e) => setNumQ(Number(e.target.value))}
                />
              </div>
              <div className={styles.field}>
                <label>Difficulty</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                >
                  {DIFFICULTIES.map((d) => (
                    <option key={d} value={d}>
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button type="submit" className={styles.generateBtn} disabled={loading || !topic.trim()}>
              {loading ? (
                <>
                  <Loader2 size={18} className={styles.spinner} />
                  Generating...
                </>
              ) : (
                "Generate Quiz"
              )}
            </button>
          </form>

          {error && <p className={styles.error}>{error}</p>}
        </div>
      ) : (
        <div className={styles.quizView}>
          <div className={styles.quizHeader}>
            <h2>Quiz: {topic}</h2>
            <button onClick={handleReset} className={styles.resetBtn}>
              <RotateCcw size={16} /> New Quiz
            </button>
          </div>

          {showResults && (
            <div className={styles.scoreCard}>
              Score: <strong>{score}</strong> / {quiz.length} (
              {Math.round((score / quiz.length) * 100)}%)
            </div>
          )}

          <div className={styles.questions}>
            {quiz.map((q, qi) => (
              <div key={qi} className={styles.questionCard}>
                <p className={styles.qText}>
                  <span className={styles.qNum}>{qi + 1}.</span> {q.question}
                </p>
                <div className={styles.options}>
                  {q.options.map((opt) => {
                    let cls = styles.option;
                    if (showResults) {
                      if (opt === q.correct_answer) cls += ` ${styles.correct}`;
                      else if (answers[qi] === opt) cls += ` ${styles.wrong}`;
                    } else if (answers[qi] === opt) {
                      cls += ` ${styles.selected}`;
                    }
                    return (
                      <button
                        key={opt}
                        className={cls}
                        onClick={() => selectAnswer(qi, opt)}
                      >
                        {showResults && opt === q.correct_answer && (
                          <CheckCircle2 size={16} />
                        )}
                        {showResults && answers[qi] === opt && opt !== q.correct_answer && (
                          <XCircle size={16} />
                        )}
                        <span>{opt}</span>
                      </button>
                    );
                  })}
                </div>
                {showResults && q.explanation && (
                  <p className={styles.explanation}>{q.explanation}</p>
                )}
              </div>
            ))}
          </div>

          {!showResults && (
            <button
              onClick={handleSubmit}
              className={styles.submitBtn}
              disabled={Object.keys(answers).length < quiz.length}
            >
              Submit Answers
            </button>
          )}
        </div>
      )}
    </div>
  );
}
