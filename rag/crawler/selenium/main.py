from scraper import start_single_crawl_but_all_courses
from transcribe import process_transcribe_queue
import multiprocessing
import argparse
import os


def main(username, password):
    os.environ["ISIS_COURSE_ID"] = "43321"
    video_queue = multiprocessing.Queue()
    crawling_start_process = multiprocessing.Process(target=start_single_crawl_but_all_courses, args=(video_queue, username, password))
    transcribtion_process = multiprocessing.Process(target=process_transcribe_queue, args=(video_queue,))
    crawling_start_process.start()
    transcribtion_process.start()
    crawling_start_process.join()
    transcribtion_process.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the scraper with user credentials.')
    parser.add_argument('username', type=str, help='Your username token')
    parser.add_argument('password', type=str, help='Your password token')

    args = parser.parse_args()

    main(args.username, args.password)
