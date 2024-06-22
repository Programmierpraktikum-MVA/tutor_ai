from scraper import start_crawl
from dropboxUpload import process_queue
from transcribe import process_transcribe_queue
import multiprocessing
import argparse


def main(username, password):
    video_queue = multiprocessing.Queue()
    final_queue = multiprocessing.Queue()
    crawling_start_process = multiprocessing.Process(target=start_crawl, args=(video_queue, username, password))
    dropbox_queue_uploading = multiprocessing.Process(target=process_queue, args=(final_queue,))
    transcribtion_process = multiprocessing.Process(target=process_transcribe_queue, args=(video_queue, final_queue,))
    crawling_start_process.start()
    transcribtion_process.start()
    dropbox_queue_uploading.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the scraper with user credentials.')
    parser.add_argument('username', type=str, help='Your username token')
    parser.add_argument('password', type=str, help='Your password token')

    args = parser.parse_args()

    main(args.username, args.password)
