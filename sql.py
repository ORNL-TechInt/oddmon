import sys
import logging
import sqlite3

ARGS = None
logger = None

class G:
    url = None
    conn = None
    config = None

def create_table():
    if G.conn is None:
        G.conn = sqlite3.connect(G.url)
    c = G.conn.cusor()

    # create table

    c.execute('''
              CREATE TABLE OSTs(
                Timestamp TEXT,
                Metric TEXT,
                Target TEXT,
                Attributes TEXT)
              ''')

    c.commit()

def insert_row():
    if G.conn is None:
        G.conn = sqlite3.connect(G.url)


def main(url):
    logger = logging.getLogger("main.%s" % __name__)
    G.url = url



