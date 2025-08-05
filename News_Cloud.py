# 필요한 라이브러리들을 가져옵니다.
# pip install wordcloud matplotlib numpy konlpy
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re # 정규 표현식 사용을 위한 라이브러리
import os # 파일 및 디렉토리 작업을 위한 라이브러리
try:
    from konlpy.tag import Okt # KoNLPy의 Okt 형태소 분석기
except ImportError:
    print("="*50)
    print("오류: konlpy 라이브러리를 찾을 수 없습니다.")
    print("KoNLPy를 설치해주세요: pip install konlpy")
    print("KoNLPy는 Java(JDK) 설치가 필요할 수 있습니다.")
    print("="*50)
    exit() # 라이브러리가 없으면 프로그램 종료

# 한국어 불용어(분석에서 제외할 명사) 목록 예시입니다. 필요에 따라 추가/수정하세요.
# 형태소 분석 후 명사만 추출하므로, 불필요하다고 생각되는 명사를 추가합니다.
STOP_WORDS = [
    '이', '그', '저', '것', '수', '등', '들', '및', '년', '월', '일', '위해', '통해',
    '때문', '관련', '전망', '가운데', '가장', '먼저', '해당', '바로', '역시', '기자',
    '오전', '오후', '여기', '우리', '하나', '정도', '가지', '경우', '이번', '당시',
    '문제', '상황', '부분', '내용', '결과', '측면', '최근', '현재', '지금', '다른',
    '대한', '대해', '위한', '이드' # 자주 등장하지만 분석에 불필요할 수 있는 명사 추가
]

# *** 형태소 분석기가 분리하지 않아야 할 단어 목록 ***
# 여기에 고유명사, 신조어 등 하나의 단위로 처리되어야 할 단어들을 추가합니다.
# (분석 전 임시 단어로 치환했다가 분석 후 복원하는 방식으로 처리됩니다)
CUSTOM_NOUNS = ['티앤엘'] # 예: ['티앤엘', '다른단어']

# --------------------------------------------------------------------------
# 데이터 로딩 (파일에서 뉴스 기사 텍스트 데이터 로딩)
# --------------------------------------------------------------------------
# 스크립트 파일의 실제 위치를 기준으로 news_data 폴더 경로를 설정합니다.
try:
    script_directory = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # 대화형 환경(예: Jupyter Notebook)에서는 __file__ 변수가 없을 수 있습니다.
    script_directory = os.getcwd()
    print("경고: __file__ 변수를 찾을 수 없어 현재 작업 디렉토리를 기준으로 합니다.")
    print(f"현재 작업 디렉토리: {script_directory}")
    print("스크립트를 .py 파일로 저장하고 실행하는 것을 권장합니다.")

news_data_directory = os.path.join(script_directory, 'news_data') # <--- 'news_data' 폴더 이름을 정확히 확인하세요!

news_articles = [] # 기사 내용을 저장할 리스트

print(f"뉴스 기사 파일을 로딩합니다: {news_data_directory}")

try:
    # 지정된 디렉토리의 모든 파일을 확인합니다.
    if not os.path.isdir(news_data_directory):
         raise FileNotFoundError(f"지정된 디렉토리를 찾을 수 없거나 디렉토리가 아닙니다: {news_data_directory}")

    for filename in os.listdir(news_data_directory):
        # 텍스트 파일(.txt)만 처리합니다.
        if filename.endswith(".txt"):
            file_path = os.path.join(news_data_directory, filename)
            try:
                # 파일을 UTF-8 인코딩으로 엽니다.
                with open(file_path, 'r', encoding='utf-8') as f:
                    news_articles.append(f.read()) # 파일 내용을 읽어 리스트에 추가
                print(f" - 로딩 성공: {filename}")
            except Exception as e:
                print(f" ! 로딩 실패: {filename} - 오류: {e}")
    print(f"총 {len(news_articles)}개의 뉴스 기사를 로딩했습니다.")

except FileNotFoundError as e:
    print(f"오류: {e}")
    print("news_data_directory 경로와 해당 폴더가 실제로 존재하는지 확인해주세요.")
    # exit() # 프로그램 중단 필요시 주석 해제

except Exception as e:
    print(f"디렉토리 처리 중 오류 발생: {e}")
    # exit() # 프로그램 중단 필요시 주석 해제


# --------------------------------------------------------------------------
# 텍스트 전처리 (형태소 분석기 사용 + 단어 대체)
# --------------------------------------------------------------------------
word_counts = Counter() # 단어 빈도 저장용 Counter 초기화
meaningful_words = [] # 의미있는 단어 저장용 리스트 초기화

if news_articles: # 로딩된 기사가 있을 경우에만 처리
    # Okt 형태소 분석기 객체 생성
    okt = Okt()

    print("\n형태소 분석을 시작합니다 (시간이 걸릴 수 있습니다)...")

    # 모든 기사를 하나의 문자열로 합칩니다.
    full_text = " ".join(news_articles)

    # 1. 사용자 정의 명사를 임시 문자열로 치환
    #    (형태소 분석기가 분리하지 못하도록)
    placeholder_map = {} # 원본 단어와 임시 문자열 매핑
    processed_text = full_text
    for i, noun in enumerate(CUSTOM_NOUNS):
        placeholder = f"CUSTOMNOUNPLACEHOLDER{i}" # 고유한 임시 문자열 생성
        processed_text = processed_text.replace(noun, placeholder)
        placeholder_map[placeholder] = noun # 매핑 정보 저장
        print(f"단어 치환: '{noun}' -> '{placeholder}'")

    # 2. (선택적) 기본적인 전처리: 한글, 영어, 숫자, 공백 외 제거
    #    임시 문자열(영어+숫자)이 제거되지 않도록 주의
    processed_text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', processed_text) # 특수문자를 공백으로 치환

    # 3. 형태소 분석기를 이용해 명사(Nouns)만 추출
    nouns = okt.nouns(processed_text)

    # 4. 임시 문자열을 다시 원본 단어로 복원
    corrected_nouns = []
    for noun in nouns:
        if noun in placeholder_map:
            corrected_nouns.append(placeholder_map[noun]) # 원본 단어로 복원
        else:
            corrected_nouns.append(noun)

    # 5. 불용어 제거 및 한 글자 명사 제거
    meaningful_words = [noun for noun in corrected_nouns if noun not in STOP_WORDS and len(noun) > 1]

    print(f"형태소 분석 완료. 총 {len(meaningful_words)}개의 유효 명사를 추출했습니다.")

    # --------------------------------------------------------------------------
    # 단어 빈도 계산
    # --------------------------------------------------------------------------
    if meaningful_words:
        word_counts = Counter(meaningful_words)

        # 가장 빈번하게 등장하는 상위 N개 단어 출력 (예: 상위 30개)
        print("\n가장 많이 사용된 명사 (상위 30개):")
        for word, count in word_counts.most_common(30):
            print(f"{word}: {count}")
    else:
        print("\n분석할 유효 명사가 없습니다.")

else:
    print("\n로딩된 뉴스 기사가 없어 분석을 건너<0xEB><0x81><0x81>니다.")


# --------------------------------------------------------------------------
# 워드 클라우드 생성 및 시각화 (분석된 단어가 있을 경우에만 진행)
# --------------------------------------------------------------------------
if word_counts: # 계산된 단어 빈도가 있을 경우에만 시각화
    # 워드 클라우드를 생성합니다.
    # font_path: 한글을 지원하는 폰트 파일의 경로를 지정해야 합니다.
    try:
        # 시스템에 설치된 폰트 경로 예시 (macOS 환경에 맞게 수정 필요)
        font_path = '/Library/Fonts/AppleGothic.ttf' # macOS 기본 고딕 폰트 예시

        # 폰트 파일 존재 여부 확인
        if not os.path.isfile(font_path):
             alternative_font_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
             if os.path.isfile(alternative_font_path):
                 font_path = alternative_font_path
                 print(f"알림: 기본 폰트 경로({font_path})를 찾을 수 없어 대체 경로({alternative_font_path})를 사용합니다.")
             else:
                 raise FileNotFoundError(f"지정된 한글 폰트 파일을 찾을 수 없습니다: {font_path} 및 대체 경로")

        wordcloud = WordCloud(
            font_path=font_path,
            width=800,
            height=400,
            background_color='white',
            max_words=100
        ).generate_from_frequencies(word_counts)

        # 워드 클라우드를 화면에 표시합니다.
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('뉴스 기사 명사 빈도 워드 클라우드') # 제목 수정
        plt.show()

    except FileNotFoundError as e:
        print("="*50)
        print(f"오류: {e}")
        print(f"font_path 경로를 시스템에 설치된 한글 폰트 파일 경로로 수정해주세요.")
        print("macOS 예시: '/Library/Fonts/AppleGothic.ttf', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'")
        print("="*50)
    except Exception as e:
        print(f"워드 클라우드 생성 중 오류 발생: {e}")

# --------------------------------------------------------------------------
# (선택) 막대 그래프로 상위 N개 단어 빈도 시각화 (분석된 단어가 있을 경우에만 진행)
# --------------------------------------------------------------------------
if word_counts: # 계산된 단어 빈도가 있을 경우에만 시각화
    try:
        # matplotlib에서 한글 폰트를 사용하도록 설정 (macOS)
        plt.rcParams['font.family'] = 'AppleGothic' # macOS 기본 폰트 설정 예시
        plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

        top_n = 20 # 상위 몇 개 단어를 보여줄지 결정
        top_words = word_counts.most_common(top_n)
        labels, values = zip(*top_words) # 단어와 빈도 분리

        plt.figure(figsize=(12, 6))
        plt.bar(labels, values, color='skyblue')
        plt.xlabel('명사') # 라벨 수정
        plt.ylabel('빈도수')
        plt.title(f'뉴스 기사 상위 {top_n}개 명사 빈도수') # 제목 수정
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"막대 그래프 생성 중 오류 발생: {e}")
        print(f"matplotlib에 설정된 한글 폰트('{plt.rcParams['font.family']}')를 찾을 수 없거나 문제가 있을 수 있습니다.")

