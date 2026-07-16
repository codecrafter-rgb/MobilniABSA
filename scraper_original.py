import requests
from bs4 import BeautifulSoup
import csv
import sys
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def scrape_phone_page(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Phone name
    phone_name = soup.select_one("span.text-2xl")
    phone_name = phone_name.get_text(" ", strip=True) if phone_name else ""


    comments = []
        
    main_comments = soup.select("div.ml-2.text-sm.leading-none.laptop\\:ml-0")
    
    for main in main_comments:
        author = main.select_one("span.font-bold").get_text(strip=True)
        date = main.select_one("span.font-hairline").get_text(" ", strip=True)

        question = main.select_one("div.commentbluelinks").get_text("\n", strip=True)
        question.replace('\n', "")
        question.replace('"', "")
        
        comments.append({
             "author": author,
             "date": date,
             "text": question
        })
        

    return {
        "phone_name": phone_name,
        "url": url,
        "question": question,
        "comments": comments
    }
    


# Access arguments by their position
if len(sys.argv) > 1:
    print(f"First argument: {sys.argv[1]}")
url = sys.argv[1]
data = scrape_phone_page(url)


with open("comments.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    writer.writerow([
        "phone_name",
        "url",
        "author",
        "date",
        "comment"
    ])
    
    
    phone_name = data["phone_name"]
    
    for c in data["comments"]:
        writer.writerow([
            phone_name,
            url,
            c["author"],
            c["date"],
            c["text"]
        ])
        
        print([phone_name,url,c["author"], c["date"], c["text"]])
        
        