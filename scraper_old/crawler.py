import requests
import re
import random
import time
import sys
import csv

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

page_number = 150 # number of search pages to read
max_comment_pages = 5 #max number of comment pages
phone_link_regex = 'href="(\/mobilni)(\/\w+\/\S+\/\S+)"'
num = 0
search_url = "https://mobilnisvet.com/mobilni-pretraga/o..minprice~f.."

url_set = set()

def get_phones_on_page(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    
    print("URL: "+url)
    
    page_set = set()
    
    html_content = r.text
    
    results = re.findall(phone_link_regex, html_content)
    
    for res in results:
        page_set.add(res[0]+'-komentari'+res[1])
    
    print(page_set)
    
    for index, item in enumerate(page_set):
        url_set.add(item)
    
    
block_size = 5 #save to csv
start_from_page = 0

if len(sys.argv) > 1:
    print(f"First argument: {sys.argv[1]}")
    start_from_page = sys.argv[1]
    
print("Starting from block "+str(start_from_page))


def main():

    with open("sitemap.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        

        for i in range(int(start_from_page), page_number):
            url = search_url+str(i)
            
            get_phones_on_page(url)
            
            time.sleep(2+random.random()) #pause
            
            if(i % block_size == 0 and i != 0):
                print("Saving to file")
                file.seek(0,0)
                file.truncate(0)
                
                #writer.writerow([
                #    "i",
                #    "url"
                #])
                
                for index,item in enumerate(url_set):
                    writer.writerow([
                        index,
                        item
                    ])
                file.flush()

        
        
if __name__ == "__main__":
    main()
    