import requests
from bs4 import BeautifulSoup
import csv
import sys
import re
import time
import random
import cyrtranslit

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def to_latin_script(input):
    return cyrtranslit.to_latin(input, "sr")


def scrape_phone_page(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Phone name
    
    phone_regex = "\/([^/]+)\/([^/]+)\/\d+$"
    match = re.search(phone_regex, url)
    phone_name = match.group(1)+" "+match.group(2)
    
    comments = []
        
    main_comments = soup.select("div.ml-2.text-sm.leading-none.laptop\\:ml-0")
    
    for main in main_comments:
        author = main.select_one("span.font-bold").get_text(strip=True)
        date = main.select_one("span.font-hairline").get_text(" ", strip=True)

        question = main.select_one("div.commentbluelinks").get_text("\n", strip=True)
        #question.replace('\n', "")
        #question.replace('"', "")
        question = to_latin_script(question)
        
        comments.append({
             "author": author,
             "date": date,
             "text": question
        })
    if(len(comments)==0):
        return None
        

    return {
        "phone_name": phone_name,
        "url": url,
        "question": question,
        "comments": comments
    }
    
    
max_comment_pages = 5 #max number of comment pages

sitemap = []

block_size = 50 #save to csv
start_from_block = 0
    
def load_sitemap(input):
    with open(input, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            sitemap.append(row)
        #print(sitemap)
        
        


# Access arguments by their position
if len(sys.argv) > 1:
    print(f"First argument: {sys.argv[1]}")
    #url = sys.argv[1]
    start_from_block = int(sys.argv[1])

base_url = "https://mobilnisvet.com"

def main():
    load_sitemap("sitemap.csv")
    
    block_data = []
    
    #popped = [sitemap.pop(0) for _ in range(start_from_block*block_size)]
    
    for i in range(start_from_block*block_size, len(sitemap)):
        if(i % block_size == 0):
            print("Starting from block "+str(i//block_size))
        print("i: "+str(i))
        for j in range(1,max_comment_pages+1):
            url = base_url + sitemap[i][1] + '/'+ str(j)
            
            print("URL: "+url)
            
            res = scrape_phone_page(url)
            if res is not None:
                block_data.append(res)
            else:
                break
            
            time.sleep(2+random.random()) #pause
        
        #for item in data_page:
        #    data.append(item)
        
        if(i % block_size == 0 and i != 0):
            block_number = i // block_size
            file = open(f"comments_{block_number}.csv", "w", newline="", encoding="utf-8")
            
            print("Writing block number "+str(block_number)+" to file")
            
            writer = csv.writer(file)
    
            if i == block_size: #first block with header
                writer.writerow([
                    "phone_name",
                    "url",
                    "author",
                    "date",
                    "comment"
                ])
            
            for k in range(0, len(block_data)):
                phone_name = block_data[k]["phone_name"]
                
                for c in block_data[k]["comments"]:
                    writer.writerow([
                        phone_name,
                        url,
                        c["author"],
                        c["date"],
                        c["text"]
                    ])
                    
                print([phone_name,url,c["author"], c["date"], c["text"]])
            
            file.flush()
            file.close()
            
            block_data = []
        
    
            
        
if __name__ == "__main__":
    main()