from scraper import start_crawl
from dropboxUpload import process_queue
import multiprocessing

def main():
    video_queue = multiprocessing.Queue()  # Use multiprocessing.Queue instead of queue.Queue
    crawling_start_process = multiprocessing.Process(target=start_crawl, args=(video_queue,))
    dropbox_queue_uploading = multiprocessing.Process(target=process_queue, args=(video_queue,))
    crawling_start_process.start()
    dropbox_queue_uploading.start()

if __name__ == "__main__":
    main()
