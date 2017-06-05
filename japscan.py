#!/usr/bin/env python2.7

import sys, os
import shutil
import sh
import requests
import pickle
from bs4 import BeautifulSoup
from optparse import OptionParser
import pickle

SITE = "http://www.japscan.com"
SITE_TITLE_NO_SUCH_MANGA = "Les Meilleurs Mangas Japonais En Lecture En Ligne | JapScan.Com"
SITE_TITLE_HEADER = "Lecture En Ligne Des Chapitres"
DB_CACHE = ".japscanrc"

class Manga:
    def __init__(self, manga, title):
        self.manga = manga
        self.title = title
        self.downloaded_chapters = set()
    def __str__(self):
        return "Manga: {0}, Title: {1}, Downloaded Chapters: {2}".format(self.manga, self.title, self.downloaded_chapters)

def get_db_cache(read=True):
    home = os.getenv("HOME")
    db = "{0}/{1}".format(home, DB_CACHE)
    return open(db, 'rb' if read else 'wb')

def get_chapter_pages (manga, chapter):
    chapter_url = "{0}/lecture-en-ligne/{1}/{2}".format(SITE, manga, chapter)
    r = requests.get(chapter_url)
    soup = BeautifulSoup(r.text, "html.parser")
    pages = soup.find(id="pages").find_all('option')
    pg = []
    for p in pages:
        pg.append(p.get('value').split('/')[-1])
    return pg

def get_page_image (manga, chapter, page):
    page_url = "{0}/lecture-en-ligne/{1}/{2}/{3}".format(SITE, manga, chapter, page)
    r = requests.get(page_url)
    soup = BeautifulSoup(r.text, "html.parser")
    src = soup.find(id='image').get('src')
    if "__Add__" in src: # dummy image, discard
        return None
    return src

def get_manga_html(manga):
    manga_url = "{0}/mangas/{1}/".format(SITE, manga)
    if options.verbose:
        print "Trying to fetch from {0}".format(manga_url)
    r = requests.get(manga_url)

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.string
    if title == SITE_TITLE_NO_SUCH_MANGA:
        print "Manga {0} can't be found ! Aborting".format(manga)
        sys.exit(1)
    title = title[len(SITE_TITLE_HEADER) + 1:].split('|')[0].strip()
    return soup, title

def get_volumes_and_chapters(html):
    chapters = html.find(id="liste_chapitres")

    vdict = {}
    if options.verbose: print "Retrieving volumes list ..."
    volumes = chapters.find_all('h2')
    vlist = []
    vlist.append("Volume Unreleased")
    for v in volumes: vlist.append(v.string)
    if options.verbose:
        print "Retrieving chapters list ..."
    i = 0
    ul = chapters.find_all('ul')
    last_chapter = 0
    for c in ul:
        chaps = []
        for ch in c.find_all('a'):
            cha = ch.get('href').split('/')[-2]
            if last_chapter == 0: last_chapter = cha
            chaps.append(cha)
        vdict[vlist[i]] = chaps
        i += 1
    return vdict, vlist, last_chapter


def get_manga_info(manga):
    html, title = get_manga_html(manga)
    vdict, vlist, last_chapter = get_volumes_and_chapters(html)

    print "{0} has the following {1} volumes, totalizing {2} chapters".format(title, len(vlist), last_chapter)
    for v in vlist:
        print " - {0}".format(v)

def parse_range_options(opt):
    if ',' in opt:
        v = opt.split(',')
        return v
    elif '-' in opt:
        v = opt.split('-')
        r = range(int(v[0]), int(v[-1])+1)
        return r
    return [int(opt)]

def find_book_by_chapter(vd, c):
    for k in vd.keys():
        if str(c) in vd[k]:
            return k
    return "Unknown"

def download_chapter(manga, out, chapter):
    pages = get_chapter_pages (manga, chapter)

    # Saving images
    real_pages = []
    for p in pages:
        img_nr = p.split('.')[0]
        img_path = "{0}/{1}.jpg".format(out, img_nr)
        if os.path.exists(img_path):
            continue

        img = get_page_image(manga, chapter, p)
        if img is None:
            continue

        if options.verbose:
            print "Downloading image from {0}".format(img)

        file = requests.get(img, stream=True)
        with open(img_path, 'wb') as out_file:
            shutil.copyfileobj(file.raw, out_file)
        del file
        if options.verbose:
            print "  saved to {}".format(img_path)
        real_pages.append(p)

    return real_pages

def chapter_to_pdf(out, chapter, pages):
    pdf_path = "{0}/{1}.pdf".format(out, chapter)
    if os.path.exists(pdf_path):
        return

    if options.verbose:
        print "Saving chapter {0} to {1}".format(chapter, pdf_path)

    jpgs = []
    for p in pages:
        img_nr = p.split('.')[0]
        jpgs.append('{0}/{1}/{2}.jpg'.format(out, chapter, img_nr))

    pdfjoin = sh.pdfjoin.bake(_tty_out=True)
    log = pdfjoin('-o', pdf_path, '--landscape', '--rotateoversize', 'false', jpgs).stdout.strip()

def get_manga(manga, title):
    for m in scrapped_mangas:
        if manga == m.manga:
            return m
    m = Manga(manga, title)
    scrapped_mangas.append(m)
    return m

def download_manga(manga, books, chapters, output):
    html, title = get_manga_html(manga)
    vdict, vlist, last_chapter = get_volumes_and_chapters(html)

    mg = get_manga(manga, title)

    # if specified, prefer books/volumes over individual chapters
    # if none is specified, download everything
    chapters_to_fetch = []
    if books:
        volumes = parse_range_options(books)
        if options.verbose:
            print "Volumes to be retrieved:", volumes
        for v in volumes:
            for k in vdict.keys():
                volume_nr = k.split(':')[0][len("Volume "):-1]
                if str(volume_nr) == str(v):
                    if options.verbose:
                        print "Found maching book:", k
                    chapters_to_fetch += vdict[k]
    elif chapters:
        chap = parse_range_options(chapters)
        chapters_to_fetch += chap
    else:
        for k in vdict.keys():
            chapters_to_fetch += vdict[k]

    chapters_to_fetch = sorted(chapters_to_fetch)
    if options.verbose:
        print "Chapters to be retrieved:", chapters_to_fetch

    # Create output dir
    base_out = "{0}/{1}".format(output, title)
    if not os.path.exists(base_out):
        os.makedirs(base_out)

    for c in chapters_to_fetch:
        book = find_book_by_chapter(vdict, c)
        print book
        book_out = "{0}/{1}".format(base_out, book)
        if not os.path.exists(book_out):
            os.makedirs(book_out)

        if options.verbose:
            print "Retrieving pages from chapter {0} ...".format(c)

        chapter_out = "{0}/{1}".format(book_out, c)
        if not os.path.exists(chapter_out):
            os.makedirs(chapter_out)

        pages = download_chapter(manga, chapter_out, c)
        chapter_to_pdf(book_out, c, pages)
        mg.downloaded_chapters.add(c)
        pickle.dump(scrapped_mangas, get_db_cache(False))

####################
# main entry point #
####################

# use UTF-8 encoding instead of unicode to support more characters
reload(sys)
sys.setdefaultencoding("utf-8")

# parse options
parser = OptionParser()
parser.add_option("-v", "--verbose", dest="verbose",
                  action="store_true", default=False,
                  help="add extra debugging information")
parser.add_option("-i", "--info", dest="info",
                  action="store_true", default=False,
                  help="display info on specified manga and exit with grace")
parser.add_option("-l", "--list", dest="list_all",
                  action="store_true", default=False,
                  help="lits all available mangas")
parser.add_option("-m", "--manga", dest="manga",
                  action="store", default="",
                  help="manga to be scraped")
parser.add_option("-b", "--books", dest="books",
                  action="store", default="",
                  help="books to be retrieved (default all)")
parser.add_option("-o", "--output", dest="output",
                  action="store", default="output",
                  help="manga to be scraped")
parser.add_option("-c", "--chapters", dest="chapters",
                  action="store", default="",
                  help="chapters to be retrieved (default all)")

(options, args) = parser.parse_args()

# either list all possible mangas or retrieve one
if options.list_all:
    print 'Listing all available mangas ...'
    list_mangas()
    sys.exit(0)
elif options.manga:
    if options.info:
        print 'Retrieving info on {} ...'.format(options.manga)
        get_manga_info(options.manga)
        sys.exit(0)
    else:
        print 'Scraping on {} ...'.format(options.manga)

        try:
            fdb = get_db_cache(True)
            scrapped_mangas = pickle.load(fdb)
        except:
            scrapped_mangas = []
        print scrapped_mangas
        download_manga(options.manga, options.books, options.chapters, options.output)
        sys.exit(0)
else:
    print parser.print_help()
    sys.exit(1)
