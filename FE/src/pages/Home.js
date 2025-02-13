import React, { useState } from 'react';
import { askQuestion } from '../utils/api';
import Header from '../components/Header';
import Footer from '../components/Footer';
import './Home.css'; // 스타일 적용

const Home = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]); // 질문 히스토리 저장

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!question.trim()) {
      setError('Question cannot be empty!');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion(question);
      setAnswer(response);

      // 히스토리에 질문과 답변 저장
      setHistory((prevHistory) => [
        { question, answer: response },
        ...prevHistory,
      ]);
    } catch (err) {
      setError('Error fetching answer. Please try again later.');
    } finally {
      setLoading(false);
      setQuestion('');
    }
  };

  return (
    <div className="home-container">
      <Header />
      <main className="main-content">
        <h2>LLM Question & Answer Service</h2>
        <p>질문을 던지고 AI 모델에게 답변을 받으세요!</p>
        <form className="question-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question here..."
            className="question-input"
          />
          <button type="submit" className="submit-btn">
            Submit
          </button>
        </form>

        {loading && <p className="loading-message">Fetching answer...</p>}
        {error && <p className="error-message">{error}</p>}
        {answer && (
          <div className="answer-card">
            <h3>Answer:</h3>
            <p>{answer}</p>
          </div>
        )}

        {history.length > 0 && (
          <div className="history-section">
            <h3>Previous Questions</h3>
            <ul>
              {history.map((entry, index) => (
                <li key={index} className="history-item">
                  <strong>Q:</strong> {entry.question}
                  <br />
                  <strong>A:</strong> {entry.answer}
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
};

export default Home;
