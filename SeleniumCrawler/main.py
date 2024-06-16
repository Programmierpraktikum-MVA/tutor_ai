import queue
from scraper import start_crawl
from dropbox import process_queue
import multiprocessing
def main():
    video_queue = queue.Queue()
    crawling_start_process = multiprocessing.process(target = start_crawl(video_queue))
    dropbox_queue_uploading = multiprocessing.Process(target =process_queue(video_queue))
    crawling_start_process.start()
    dropbox_queue_uploading.start()

if __name__ == "__main__":
    main()