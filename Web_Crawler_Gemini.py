import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

# --- Configuration ---
# Main entry point for CVPR 2025 papers
BASE_URL = "https://openaccess.thecvf.com/CVPR2025" 
SEARCH_KEYWORD = "deep learning"
OUTPUT_FILE = "cvpr_2025_deep_learning_papers.csv"
USER_AGENT = "CVPR_Crawler_Bot/1.0 (+https://yourdomain.com)"

def check_robots_txt(url, user_agent):
    """Parses robots.txt to ensure we are allowed to scrape."""
    robots_url = urljoin(url, "/robots.txt")
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception as e:
        print(f"Warning: Could not read robots.txt ({e}). Proceeding with caution.")
        return True # Default to True if robots.txt is missing/unreadable

def extract_paper_metadata(paper_url):
    """Visits individual paper pages to extract the abstract and full metadata."""
    try:
        # Polite delay to avoid overwhelming the CVF servers
        time.sleep(1) 
        
        response = requests.get(paper_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract Abstract
        abstract_div = soup.find('div', id='abstract')
        abstract = abstract_div.text.strip() if abstract_div else ""
        
        # Extract Authors
        authors_div = soup.find('div', id='authors')
        if authors_div:
            # Often formatted as "Author 1; Author 2" or inside <i> tags
            authors = authors_div.text.strip().replace('\n', '').replace(';', ', ')
        else:
            authors = "Unknown"
            
        # Extract Publication Date (Usually June for CVPR)
        month_div = soup.find('div', class_='month')
        pub_date = f"June 2025" # Hardcoded backup based on conference date
        if month_div:
            pub_date = f"{month_div.text.strip()} 2025"
            
        return authors, abstract, pub_date
        
    except requests.exceptions.RequestException as e:
        print(f"Network error accessing {paper_url}: {e}")
        return None, None, None
    except Exception as e:
        print(f"Parsing error on {paper_url}: {e}")
        return None, None, None

def run_crawler():
    print(f"Checking robots.txt for {BASE_URL}...")
    if not check_robots_txt(BASE_URL, USER_AGENT):
        print("Scraping is disallowed by robots.txt. Exiting.")
        return

    papers_data = []
    current_url = f"{BASE_URL}?day=all" # Start URL
    page_num = 1

    print("Starting crawl...")
    
    while current_url:
        print(f"--- Crawling Page {page_num}: {current_url} ---")
        try:
            response = requests.get(current_url, headers={"User-Agent": USER_AGENT}, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch {current_url}: {e}")
            break

        # CVF typically lists paper titles in <dt class="ptitle">
        paper_entries = soup.find_all('dt', class_='ptitle')
        
        if not paper_entries:
            print("No papers found on this page. Stopping.")
            break

        for entry in paper_entries:
            link_tag = entry.find('a')
            if not link_tag:
                continue
                
            title = link_tag.text.strip()
            paper_url = urljoin(BASE_URL, link_tag['href'])
            
            # FAST PATH: Check if keyword is in the title first
            # To save bandwidth, we don't download the full abstract page if we don't need to.
            # However, since you want to check the abstract too, we must fetch it.
            
            authors, abstract, pub_date = extract_paper_metadata(paper_url)
            
            # Handle Missing Data
            if not abstract:
                print(f"Skipping '{title}' due to missing abstract/metadata.")
                continue
                
            # Filter by Topic (Title or Abstract)
            if (SEARCH_KEYWORD.lower() in title.lower()) or (SEARCH_KEYWORD.lower() in abstract.lower()):
                print(f"Matched: {title}")
                papers_data.append({
                    "Title": title,
                    "Authors": authors,
                    "Abstract": abstract,
                    "Publication Date": pub_date,
                    "URL": paper_url
                })

        # --- Pagination Logic ---
        # Look for a standard 'Next' link. 
        next_button = soup.find('a', string=lambda text: text and 'Next' in text)
        if next_button and 'href' in next_button.attrs:
            current_url = urljoin(BASE_URL, next_button['href'])
            page_num += 1
        else:
            current_url = None # End loop if no next page is found

    # Save extracted data
    if papers_data:
        df = pd.DataFrame(papers_data)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print(f"\nSuccess! Saved {len(df)} papers to '{OUTPUT_FILE}'.")
    else:
        print(f"\nFinished crawling, but no papers matching '{SEARCH_KEYWORD}' were found.")

if __name__ == "__main__":
    run_crawler()