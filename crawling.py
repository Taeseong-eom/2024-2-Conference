from bs4 import BeautifulSoup as bs
import pandas as pd
from selenium import webdriver # selenium
from selenium.webdriver.chrome.options import Options # headless 옵션 
from datetime import datetime 
import time
from pymongo import MongoClient # DB 
from dotenv import load_dotenv
import os
import re 

# MongoDB 연결
load_dotenv() # .env 파일 로드
connection_string = os.environ.get("MONGO_URI")

client = MongoClient(connection_string, tls=True, tlsAllowInvalidCertificates=True)
db = client['Conference'] # DB 선택
article_col = db['article'] # Collection 선택 

sections = {100: '정치',
            101: '경제', 
            102: '사회', 
            103: '생활문화',
            105: 'IT과학', 
            104: '세계', 
            }

news_cnt = 5 # section별로 크롤링 해올 기사 개수 지정
re_blank = True # 공백 제거 여부 설정 # 제거: True 

news_li = []
now_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 크롤링 할 때의 시간 저장 
for section_num, section_name in sections.items(): # 각 section별 
    url = f"https://news.naver.com/section/{section_num}" # url 설정 
    prev_date_time = None # 이전 기사 날짜 저장 

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 창 안뜨게 하는 옵션
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    time.sleep(2) # 페이지 로딩 대기 

    html = driver.page_source
    soup = bs(html, 'html.parser')
    articles = soup.select("div.sa_text")

    for article in articles[0:news_cnt]: # news_cnt=3 -> 1~3번째 기사 수집 
        news = {}
        news["section"] = section_name # 기사 분야 
        news["title"] = article.select_one("strong.sa_text_strong").get_text() # 제목
        news["url"] = article.select_one("a.sa_text_title")["href"] # url 링크
        news["press"] = article.select_one("div.sa_text_press").get_text() # 출판사

        response = driver.get(news["url"]) # 기사 본문으로 이동 
        html = driver.page_source
        soup = bs(html, 'html.parser')
        
        date_tag = soup.select_one("span.media_end_head_info_datestamp_time") # 기사가 쓰여진 날짜 저장
        if date_tag: # 해당 태그가 있으면 기사 날짜 저장 
            date_time = date_tag["data-date-time"] 
            prev_date_time = date_time # 바로 전 기사의 날짜 저장
        else: # 없으면 이전 기사의 날짜 정보 사용 
            date_time = prev_date_time if prev_date_time else now_date_time
            print(f"해당 기사의 날짜 정보를 찾을 수 없습니다. 기사 링크: {news['url']}")
        date = date_time.split()[0] # 크롤링 날짜는 now_date_time
        news["date"] = date # 날짜 ex) 2025-02-12

        video_tag = soup.select_one('div.vod_player_wrap') # 비디오 플레이어 영역이 있으면
        if video_tag: # 비디오 플레이어 다음부터
            content = " ".join([a.strip() for a in video_tag.next_siblings if isinstance(a,str)])
        else: # 아니면 텍스트 전체 
            content = soup.select_one('article#dic_area').get_text() # 기사 본문 
        if re_blank: # 공백 제거 
            content = re.sub(r"\n+", "", content).strip() 
        news["content"] = content

        news_li.append(news)
        
    driver.quit()

# csv로 저장 
# news_df = pd.DataFrame(news_li) # pandas DataFrame으로 변경 
# news_df.to_csv("news_data.csv")

# MongoDB에 저장
article_col.insert_many(news_li) # 컬렉션에 데이터 삽입 
# print(f"{len(news_li)}개의 데이터를 저장했습니다.")