import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import retry
from pymongo import MongoClient
from langchain.tools import Tool

# 환경 변수 로드
load_dotenv()
gemini_api = os.environ.get("Gemini_API_KEY")
genai.configure(api_key= gemini_api)

# MongoDB 연결 설정
connection_string = os.environ.get("DB_connection_string")
client = MongoClient(connection_string)
db = client['Conference']
article_collection = db["article"]

# Gemini 모델 설정
model = genai.GenerativeModel("gemini-pro")

# MongoDB에서 뉴스 데이터 로드
def load_data():
    articles = list(article_collection.find({}))
    # ObjectId 등 JSON 직렬화에 문제가 되는 항목은 문자열로 변환
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


# 모델 사용해서서 date, section 추출 
def generate_date_section(user_query):
    """
    Gemini를 사용하여 사용자 입력을 MongoDB 검색 쿼리로 변환
    """
    prompt = f"""
    사용자의 질문을 분석하여, date와 section를 응답 형식에 맞추어서 알려줘.

    예제:
    - 질문: "오늘 IT 뉴스 요약해줘"
      응답: "date: 2025-02-12, section: IT과학"

    - 질문: "어제 경제 뉴스 알려줘"
      응답: "date: 2025-02-11, section: 경제"

    - 질문: "최근 정치 뉴스 요약해줘"
      응답: "date: 최근, section: 정치"

    - 질문: "요근래 정치 뉴스 요약해줘"
      응답: "date: 최근, section: 정치"

    - 질문: "요즘 정치 뉴스 요약해줘"
      응답: "date: 최근, section: 정치"

    - 질문: "일주일치 it 뉴스 요약해줘"
      응답: "date: 일주일, section: IT과학"
    
    - 질문: "{user_query}"
      응답:
    """
    
    response = model.generate_content(prompt)

    # 모델 응답 디버깅
    print("\n🔍 Gemini 응답:", response.text)

    return response.text


# 응답 분석 후, MongoDB 쿼리문 만들기, 뉴스데이터 가져오기기
def article(answer):
    date, section = None, None

    match = re.search(r"date:\s*([\w\d-]+),\s*section:\s*(\w+)", answer)
    if match:
        date = match.group(1).strip()
        section = match.group(2).strip()

    # MongoDB 쿼리 변환
    query = {}

    # 날짜 변환
    if date:

        if "최근" in date:
            query["date"] = {"$gte": (datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d")}
            date = query["date"]

        elif "일주일" in date:
            query["date"] = {"$gte": (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")}
            date = query["date"]

    # 카테고리 변환
    if section:
        query["section"] = section

    print("\n🔍 생성된 MongoDB 검색 쿼리:", query)

    # MongoDB에서 뉴스 검색
    news_articles = search_news(query)

    if not news_articles or news_articles == "해당 날짜의 뉴스가 없습니다.":
        return "해당 날짜와 카테고리에 맞는 뉴스가 없습니다."


    # MongoDB 디버깅용
    print("\n✅ MongoDB에서 가져온 뉴스 데이터:")
    for news in news_articles:
        print(f"제목: {news.get('title', '제목 없음')}")
        print(f"출처: {news.get('press', '출처 없음')}")
        print(f"날짜: {news.get('date', '날짜 없음')}")
        print(f"URL: {news.get('url', 'URL 없음')}")
        print(f"내용: {news.get('content', '내용 없음')[:100]}...")  # 내용이 길면 100자까지만 표시


    # 뉴스 기사
    news_texts = "\n\n".join([
        f"제목: {news['title']}\n날짜: {news['date']}\n내용: {news['content']}"
        for news in news_articles
    ])
    return news_texts, date, section


# 뉴스 기사 요약
def summarize(news_texts, date, section):

    # Gemini 프롬프트 설정
    prompt = f"""
        다음은 {date}의 {section} 뉴스 기사입니다. 이를 바탕으로 뉴스 요약을 제공하세요.
        1. 여러 개의 뉴스들을 보고, 공통된 흐름이나 트렌드를 알려주세요.
        2. 중요한 뉴스라고 생각된다면, 따로 요약해서 알려주세요.
        3. 전문 용어 등의 어려운 개념이 있다면 설명을 추가하세요.

        {news_texts}

        뉴스 분석:
        """

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)

    return response.text 


user_query = "요즈음 정치 뉴스 요약해줘"
answer = generate_date_section(user_query)
news_texts, date, section = article(answer)
summary = summarize(news_texts, date, section)
print(summary)