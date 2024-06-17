from scraper import start_crawl
from dropboxUpload import process_queue
from transcribe import process_transcribe_queue
import multiprocessing

def main():
    video_queue = multiprocessing.Queue()
    final_queue = multiprocessing.Queue()
    crawling_start_process = multiprocessing.Process(target=start_crawl, args=(video_queue,))
    dropbox_queue_uploading = multiprocessing.Process(target=process_queue, args=(final_queue,))
    transcribtion_process = multiprocessing.Process(target=process_transcribe_queue, args=(video_queue, final_queue,))
    crawling_start_process.start()
    transcribtion_process.start()
    dropbox_queue_uploading.start()

if __name__ == "__main__":
    main()
