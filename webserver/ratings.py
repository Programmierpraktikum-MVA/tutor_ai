import sqlite3
from sqlite3 import Error
import sys
import os

"""
Database will consist of one table:
ratings
ID(int) rating(int) question(str) answer(str) evaluated(0 or 1)
"""

db_file = r"TutorAI.db"     # path to database file
evaluation_threshold = 4    # only entrys >= threshold will be evaluated

def create_db():
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.cursor().execute("CREATE TABLE IF NOT EXISTS ratings (id integer PRIMARY KEY,rating integer NOT NULL,question text NOT NULL,answer text NOT NULL, evaluated integer )")
        
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

def create_connection():
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn

def insert_rating(rating):
    """ rating = (rating, 'question', 'answer')"""
    conn = create_connection()
    sql = """ INSERT INTO ratings(rating, question, answer, evaluated)
              VALUES(?,?,?,0) """
    cur = conn.cursor()
    cur.execute(sql, rating)
    conn.commit()
    conn.close()
    return None 

def extract(conn):
    """returns a column to evaluate"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM ratings WHERE rating >= ? AND evaluated = 0 LIMIT 1;",(evaluation_threshold,))
    return cur.fetchall()[0]

def evaluated(id, conn):
    sql = """ UPDATE ratings SET evaluated = 1 WHERE id = ?"""
    cur = conn.cursor()
    cur.execute(sql, (id,))
    conn.commit()

def number_to_evaluate(conn):
            
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ratings WHERE rating >= ? AND evaluated = 0",(evaluation_threshold,))

            good_reviews = cur.fetchone()[0]
            return good_reviews

def push_to_vdb(question, answer): #TODO
    return None

def description():
        print("This script is expecting one argument:\n ")
        print("--new \t\t to setup a new database file \n")
        print(f"--evaluate \t to go into the evaluation process of {evaluation_threshold}+ star reviews\n")
        print("--print \t to print out the current db")

if __name__ == '__main__':

    if len(sys.argv) != 2:
        description()
    else:
        if sys.argv[1] == "--new":
            if os.path.exists(db_file):
                print(f"File {db_file} already exists.")
            else:
                create_db()
                print(f"New db created: {db_file}")
                print("sqlite3 version:" + sqlite3.version)
        elif sys.argv[1] == "--evaluate":
            conn = create_connection()
            amount = number_to_evaluate(conn)
            while(amount>0):
                print(f"{amount} entries have to be evaluated (q to quit):")
                action = input()
                if action == "q":
                    break
                id, rating, question, answer, ev = extract(conn) #takes the first entry that needs to be evaluated
                print(f"Question:\n{question}\nAnswer:\n{answer}\n\n")
                accept = input("accept this entry? (y/n):")
                if accept == "y":
                    push_to_vdb(question, answer)
                
                evaluated(id, conn) #set evaluated to 1
                amount = number_to_evaluate(conn)
            conn.close()

        elif sys.argv[1] == "--print":
            conn= create_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM ratings")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()
            conn.close()

        elif sys.argv[1] == "--test":
            create_db()
            conn = create_connection()
            rating1 = (5,'Wer hält die Vorlesung für Einführung in die Programmierung?','Manfred Hauswirth')
            rating2 = (0,'Welche Programmiersprache wird in Einführung in die Programmierung gelehrt?','Java')
            insert_rating(conn, rating1)
            insert_rating(conn, rating2)
            cur = conn.cursor()
            cur.execute("SELECT * FROM ratings")
            rows = cur.fetchall()
            for row in rows:
                print(row)
            cur.close()

            conn.close()
        else:
            description()
