from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import os
import re
from datetime import datetime, timedelta
from pymongo import MongoClient
from langchain.tools import Tool

# 환경 변수 로드
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Flask 앱 설정
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# MongoDB 연결 설정
connection_string = os.environ.get("MONGO_URI")
client = MongoClient(connection_string)
db = client['Conference']
article_collection = db["article"]

# Gemini 모델 설정
model = genai.GenerativeModel("gemini-pro")

# MongoDB에서 뉴스 데이터 로드
def load_data():
    articles = list(article_collection.find({}))
    for article in articles:
        if "_id" in article:
            article["_id"] = str(article["_id"])
    return articles

# MongoDB에서 뉴스 검색
def search_news(query_dict):
    results = list(article_collection.find(query_dict, {"_id": 0, "title": 1, "content": 1, "date": 1, "url": 1, "press": 1}).limit(10))
    return results if results else "해당 날짜의 뉴스가 없습니다."

# LangChain 검색기 연결
search_tool = Tool(
    name="MongoDB News Search",
    func=search_news,
    description="MongoDB에서 뉴스 검색 (날짜와 카테고리를 입력하세요)."
)

# 모델 사용해서 date, section 추출 
def generate_date_section(user_query):
    prompt = f"""
    사용자의 질문을 분석하여, date와 section를 응답 형식에 맞추어서 알려줘.

    예제:
    - 질문: "오늘 IT 뉴스 요약해줘"
      응답: "date: 2025-02-12, section: IT과학"

    - 질문: "어제 경제 뉴스 알려줘"
      응답: "date: 2025-02-11, section: 경제"

    - 질문: "{user_query}"
      응답:
    """
    
    response = model.generate_content(prompt)
    print("\n🔍 Gemini 응답:", response.text)
    return response.text

# 응답 분석 후, MongoDB 쿼리문 만들기, 뉴스데이터 가져오기
def article(answer):
    date, section = None, None

    match = re.search(r"date:\s*([\w\d-]+),\s*section:\s*(\w+)", answer)
    if match:
        date = match.group(1).strip()
        section = match.group(2).strip()

    # MongoDB 쿼리 변환
    query = {}

    if date:
        if "최근" in date:
            query["date"] = {"$gte": (datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d")}
            date = query["date"]

        elif "일주일" in date:
            query["date"] = {"$gte": (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")}
            date = query["date"]

    if section:
        query["section"] = section

    print("\n🔍 생성된 MongoDB 검색 쿼리:", query)

    # MongoDB에서 뉴스 검색
    news_articles = search_news(query)

    if not news_articles or news_articles == "해당 날짜의 뉴스가 없습니다.":
        return "해당 날짜와 카테고리에 맞는 뉴스가 없습니다."

    print("\n✅ MongoDB에서 가져온 뉴스 데이터:")
    for news in news_articles:
        print(f"제목: {news.get('title', '제목 없음')}")
        print(f"출처: {news.get('press', '출처 없음')}")
        print(f"날짜: {news.get('date', '날짜 없음')}")
        print(f"URL: {news.get('url', 'URL 없음')}")
        print(f"내용: {news.get('content', '내용 없음')[:100]}...")

    news_texts = "\n\n".join([
        f"제목: {news['title']}\n날짜: {news['date']}\n내용: {news['content']}"
        for news in news_articles
    ])
    return news_texts, date, section

# 뉴스 기사 요약
def summarize(news_texts, date, section):
    prompt = f"""
        다음은 {date}의 {section} 뉴스 기사입니다. 이를 바탕으로 뉴스 요약을 제공하세요.
        1. 여러 개의 뉴스들을 보고, 공통된 흐름이나 트렌드를 알려주세요.
        2. 중요한 뉴스라고 생각된다면, 따로 요약해서 알려주세요.
        3. 전문 용어 등의 어려운 개념이 있다면 설명을 추가하세요.

        {news_texts}

        뉴스 분석:
        """

    response = model.generate_content(prompt)
    return response.text

# Flask API 엔드포인트
@app.route('/api/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question')

    try:
        # Step 1: 질문 분석하여 date, section 추출
        date_section = generate_date_section(question)

        # Step 2: MongoDB에서 관련 뉴스 데이터 가져오기
        news_texts, date, section = article(date_section)

        # Step 3: 뉴스 요약
        summary = summarize(news_texts, date, section)

        answer = summary

    except Exception as e:
        answer = f"An error occurred: {str(e)}"

    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
