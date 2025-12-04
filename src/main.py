import os
import re
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain_community.chat_models import ChatOpenAI
from notion_client import Client
from urllib.parse import urlparse


# Notion APIの設定 ------------------------------------------------------------------------------
load_dotenv()
Notion_API_Key = os.environ["NOTION_API_KEY"]
Notion_Database_ID = os.environ["NOTION_DATABASE_ID"]
url = f"https://api.notion.com/v1/databases/{Notion_Database_ID}/query"
openai_api_key = os.environ["OPENAI_API_KEY"]
openai.api_key = openai_api_key


# getNotionData --------------------------------------------------------------------------------------------

# 【データ格納処理】 -----------------------------------
def process_page_data(json_data, article_list):
    for page in json_data.get("results", []):
        properties = page.get("properties", {})

    # データの取得 --------------------------------
        # ブロックIDを取得
        block_id = page.get("id", [])
        # 記事のユニークIDを取得
        article_id = properties.get("ID", {}).get("unique_id", {}).get("number")
        # Title列のテキストデータを取得
        article_title = properties.get("Title", {}).get("title", [{"text": {"content": ""}}])[0]["text"]["content"]
        # URL列のテキストデータを取得
        article_url = properties.get("URL", {}).get("url", "")
        # 日付の取得
        article_date = properties.get("Date", {}).get("date", {})
        # サマリーの取得
        summary_data = properties.get("Summary", {}).get("rich_text", [])
        if summary_data:
            article_summary = summary_data[0]["text"]["content"]
        else:
            article_summary = ""
        # タグの取得
        tags_data = properties.get("Tags", {}).get("rich_text", [])
        if tags_data:
            article_tags = tags_data[0]["text"]["content"]
        else:
            article_tags = ""
        # 出典の取得
        source_data = properties.get("Source", {}).get("rich_text", [])
        if source_data:
            article_source = source_data[0]["text"]["content"]
        else:
            article_source = ""
            

    # リストへ格納 --------------------------------
        article_list.append({
            "block_id": block_id,
            "id":       article_id,
            "title":    article_title, 
            "url":      article_url,
            "date":     article_date,
            "summary":  article_summary,
            "tags":     article_tags,
            "source":   article_source,
        })

    return article_list



# 【DB情報取得】 --------------------------------
def get_article_list(Notion_API_Key, url):

    # postのヘッダー情報
    headers = {
        "Authorization": f"Bearer {Notion_API_Key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # 初期化
    article_list = []
    has_more = True
    next_cursor = None

    # データの取得 --------------------------------
    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
            payload["page_size"] = 100

        response = requests.post(url, headers=headers, json=payload)
        # print("APIレスポンス:", response.status_code, response.text)

        json_data = response.json()

        article_list = process_page_data(json_data, article_list)

        has_more = json_data.get('has_more', False)
        next_cursor = json_data.get('next_cursor', None)

    return article_list


# ConnectionConfirmation ----------------------------------------------------------------------------
def Connection_Confirmation(each_article):
    url = each_article["url"]

    # リクエストエラーの検出
    try:
        article = requests.get(url, verify = True)          # SSL検証を有効にしてリクエストを送信
        article.raise_for_status()                          # エラーが発生した場合、例外をスロー
        each_article["error_code"] = ""

    except requests.exceptions.RequestException as e:
        each_article["error_code"] = str(e)                 # エラー情報を追加
        each_article["article_text"] = ""
        each_article["summary"] = ""
        each_article["tags"] = ""
        each_article["source"] = ""

    return each_article                                     # 処理を終了し、呼び出し元に戻る


# getDate -------------------------------------------------------------------------------------------
def get_date(each_article):

    # 接続失敗 --------------------------------
    if each_article["error_code"]:
        each_article["date"] = "日付情報なし"
        return each_article


    # 接続成功 --------------------------------
    else:
        url = each_article["url"]
        article = requests.get(url, verify = True)
        soup = BeautifulSoup(article.content, "html.parser")

        article_date = None
        formatted_date = None
        date_pattern = r'\d{4}-\d{2}-\d{2}'

        # <time>タグから取得
        date_element = soup.find("time")
        if date_element:
            article_date = date_element.get_text()
            print(f"  <time>要素:{article_date}")
            

        # <meta>タグから取得
        if not article_date:
            meta_tags = soup.find_all("meta")
            for tag in meta_tags:
                if tag.get("property") == "article:modified_time":
                    article_date = tag.get("content")
                    break
                elif tag.get("property") == "date":
                    article_date = tag.get("content")
                    break
            print(f"  <meta>要素:{article_date}")
        
        # 特定のクラス名やIDから取得
        if not article_date:
            possible_date_elements = soup.find_all(attrs={"class": re.compile(r"date|time|datetime|published|the-date|cal", re.I)})
            for element in possible_date_elements:
                article_date = element.get_text().strip()
                if article_date:
                    print(f"  特定のクラス名やIDから取得:{article_date}")
                    break


        # 日付要素がある場合 --------------------------------
        if article_date:

            # 'YYYY-MM-DD' 形式に一致する場合
            if re.fullmatch(date_pattern, article_date):    
                formatted_date = article_date

            # 'YYYY-MM-DD' 形式に一致しない場合
            else:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": f"What is the date '{article_date}' in the 'yyyy-mm-dd' format?Please answer with only the results."}
                    ],
                    max_tokens=50,
                    temperature=0.5
                )
                formatted_date = response.choices[0].message['content']
                print(f"  日付要素をISO8601形式へ:{formatted_date}")

        # ISO8601形式かチェック --------------------------------
        if formatted_date:
            if re.fullmatch(date_pattern, formatted_date):    
                each_article['date'] = formatted_date    
            else:
                each_article["date"] = "日付情報なし"
                print(f"  日付の形式が正しくありません: {formatted_date}")
                
        else:
            each_article["date"] = "日付情報なし"
        
        print(f"  日付: {each_article['date']}")
    return each_article


# getArticleText --------------------------------------------------------------------------------------
def get_article_text(each_article):

    # 接続成功 --------------------------------
    if each_article["error_code"] == "":
    
        # 記事本文の取得
        url = each_article["url"]
        article = requests.get(url, verify = True)
        soup =  BeautifulSoup(article.content, "html.parser")
        article_text = soup.get_text()

        characters_to_remove = ["\n", "\t", "\r", " "]          # 不要文字リスト
        for char in characters_to_remove:                       # リスト順
            article_text = article_text.replace(char, "")       # 不要文字を削除

        # リストへ追加
        each_article["article_text"] = article_text.strip()

    return each_article


# get_source ---------------------------------------------------------------------------
def get_article_source(each_article):
    # 1. メタタグから取得
    each_article = get_source_from_meta(each_article)
    
    # 2. URLからドメイン名抽出（なければURLからの値を使う）
    if each_article["source"] in ["", None]:
        each_article = get_source_from_url(each_article)
    
    # 3. AIを使って出典名を特定（URLやメタ情報で取れなかった場合）
    if each_article["source"] in ["", None]:
        each_article = get_source_with_ai(each_article)
    
    return each_article


def get_source_from_meta(each_article):
    url = each_article["url"]
    article = requests.get(url, verify=True)
    soup = BeautifulSoup(article.content, "html.parser")

    # metaタグからサイト名を取得
    site_name = soup.find("meta", property="og:site_name")
    if site_name and site_name.get("content"):
        each_article["source"] = site_name["content"]
    else:
        each_article = get_source_from_url(each_article)  # URLから取得
    return each_article


def get_source_from_url(each_article):
    url = each_article["url"]
    parsed_url = urlparse(url)
    domain = parsed_url.netloc  # 例: "www.nhk.or.jp"
    
    # www. を削除してサイト名にする
    site_name = domain.replace("www.", "").split('.')[0].capitalize()  
    each_article["source"] = site_name
    return each_article
    

def get_source_with_ai(each_article):
    prompt = f"""
    次の文章の出典を1単語で出力してください:
    "{each_article['title']}"
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=20,
        temperature=0.5
    )
    
    each_article["source"] = response.choices[0].message["content"].strip()
    return each_article


# generateSummaryAndTags ---------------------------------------------------------------------------
def generate_summary_Tags(each_article):
    
    article_text = each_article["article_text"]

    # API設定 --------------------------------
    load_dotenv()
    openai_api_key = os.environ["OPENAI_API_KEY"]
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",       # GPT-4o mini を指定
        # max_tokens=500,               # 必要に応じて調整
        # temperature=0.5               # 応答の多様性を設定（任意）
    )


    # Question1（翻訳）
    prompt_1 = PromptTemplate(
        input_variables=["article_text"],
        template="次の文章を200字程度で要約して。言語は記事本文と同じで。語尾は断定形で: {article_text}",
    )
    chain_1 = LLMChain(llm=llm, prompt=prompt_1, output_key="article_summary")


    # Question2（タグ生成）
    prompt_2 = PromptTemplate(
        input_variables=["article_summary"],
        template=
            """
            次の記事の要約から、トピックを表すタグを生成して：
            {article_summary}. 
            登場する企業、業界、分類を表すような2～20 個の単語を、最小単位で、カンマ区切りで。
            半導体関連の記事は「半導体」というタグを必ず含めて。
            """,
    )
    chain_2 = LLMChain(llm=llm, prompt=prompt_2, output_key="article_tags")


    # チェーンの設定
    overall_chain = SequentialChain(
        chains           = [chain_1, chain_2],
        input_variables  = ["article_text"],
        output_variables = ["article_summary", "article_tags"],
        verbose          = True,
    )
    output = overall_chain({
        "article_text": article_text,
    })

# 必要な情報を抽出
    article_summary = output["article_summary"]
    each_article["summary"] = article_summary
    article_tags = output["article_tags"]
    each_article["tags"] = article_tags
    
    return each_article



# updateDataToNotion ---------------------------------------------------------------------------
def update_page_properties(Notion_API_Key, each_article):

    client = Client(auth = Notion_API_Key)              # notion-clientの利用

    if each_article["date"] != "日付情報なし":
        try:
            response = client.pages.update(
                **{
                    "page_id": each_article["block_id"],    # ここでページを識別
                    "properties": {
                        "Date": {
                            "type": "date",
                            "date": {
                                "start": each_article['date']
                                }
                            }
                    }
                }
            )
            if response.get("object") == "error":
                print(f"Update failed: {response['message']}")
            else:
                print("Date update successful.")
        except Exception as e:
            print(f"Update failed: {e}")

    if each_article["summary"]:
        try:
            response = client.pages.update(
                **{
                    "page_id": each_article["block_id"],    # ここでページを識別
                    "properties": {
                        "Summary": {
                            "type": "rich_text",
                            "rich_text": [{"text": {"content": each_article['summary']}}]
                        },
                        "Tags": {
                            "type": "rich_text",
                            "rich_text": [{"text": {"content": each_article['tags']}}]
                        },
                        "Source": {
                            "type": "rich_text",
                            "rich_text": [{"text": {"content": each_article['source']}}]
                        }
                    }
                }
            )
            if response.get("object") == "error":
                print(f"Update failed: {response['message']}")
            else:
                print("Summary and other fields update successful.")
        except Exception as e:
            print(f"Update failed: {e}")


# removeDuplicateArticles ---------------------------------------------------------------------------
def remove_duplicate_articles(Notion_API_Key, article_list):
        
    client = Client(auth=Notion_API_Key)
    url_to_article = {}  				# URLから記事データのマッピング
    duplicates_to_delete = []  	# 削除対象の記事リスト
    deleted_block_ids = set()  	# 削除された記事のblock_idを保存
    
    print("\n重複記事の検出を開始")
    
    # URL別に記事をグループ化し、重複を検出
    for article in article_list:
        url = article["url"]
        if url in url_to_article:
          # 既存の記事より新しい（IDが大きい）場合、削除対象とする
            existing_article = url_to_article[url]
            current_id = article.get("id", 0) or 0
            existing_id = existing_article.get("id", 0) or 0
            
            if current_id > existing_id:
                # 削除対象
                duplicates_to_delete.append(article)
                print(f"  重複検出: ID {current_id} '{article['title'][:50]}...' (削除対象)")
            else:
                # 保持対象
                duplicates_to_delete.append(existing_article)
                url_to_article[url] = article
                print(f"  重複検出: ID {existing_id} '{existing_article['title'][:50]}...' (削除対象)")
        else:
            url_to_article[url] = article
    
    # 重複記事を削除
    deleted_count = 0
    for duplicate in duplicates_to_delete:
        try:
            print(f"  削除中: ID {duplicate.get('id', 'N/A')} '{duplicate['title'][:50]}...'")
            
            # Notion APIでページをアーカイブ（削除）
            response = client.pages.update(
                page_id=duplicate["block_id"],
                archived=True
            )
            
            if response.get("object") == "error":
                print(f"    削除失敗: {response['message']}")
            else:
                deleted_count += 1
                deleted_block_ids.add(duplicate["block_id"])
                print(f"    削除成功")
        except Exception as e:
            print(f"    削除失敗: {e}")
    
    # 削除された記事をリストから除外
    updated_article_list = [article for article in article_list 
                           if article["block_id"] not in deleted_block_ids]
    
    print(f"\n重複記事削除完了: {deleted_count}件削除")
    print(f"更新後リスト: {len(updated_article_list)}件（削除前: {len(article_list)}件）")
    
    return updated_article_list, deleted_count


# main関数 ------------------------------------------------------------------------------
if __name__ == "__main__":

    # Notion のリスト取得
    print("\n1. Got notion-data\n")
    article_list = get_article_list(Notion_API_Key, url)
    # print("\n取得した記事リスト:", article_list)

    # 重複記事の削除
    article_list, deleted_count = remove_duplicate_articles(Notion_API_Key, article_list) 

    for each_article in article_list:

    	# 処理をする条件
      # if each_article["date"] is None:             # 日付が空の記事を処理
      if each_article["summary"] == "":              # サマリが空の記事を処理


      # リンク先の情報取得 --------------------------------
          each_article2 = Connection_Confirmation(each_article)
          if each_article2["error_code"]:
              print(f"\n2.リンク先への接続時のエラーです:\n  {each_article2['id']} / {each_article2['title']}")
          else:
              print(f"\n2.リンク先への接続成功:\n  {each_article2['id']} / {each_article2['title']}")


          # 日付の抽出 --------------------------------
              print("\n\n3. get Date infomation\n")
              each_article3 = get_date(each_article2)
              # print(f"{each_article3}\n")

          # 本文の抽出 --------------------------------
              print("\n\n4. get article text\n")
              each_article4 = get_article_text(each_article3)
              # print(f"{each_article4}\n")


          # 記事の要約 --------------------------------
              print("\n\n5. Summarize the articles\n")
              each_article5 = generate_summary_Tags(each_article4)
              # print(f"{each_article5}\n")

          
          # 出典の取得 --------------------------------
              print("\n\n6. get article source\n")
              each_article6 = get_article_source(each_article5)
              # print(f"{each_article6}\n")


          # Notion へ入力 --------------------------------
              result = update_page_properties(Notion_API_Key, each_article3)
