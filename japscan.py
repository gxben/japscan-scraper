#!/usr/bin/env python2.7

import sys, os
import shutil
import sh
import requests
import pickle
from bs4 import BeautifulSoup
from optparse import OptionParser

SITE = "http://www.japscan.com"
SITE_TITLE_NO_SUCH_MANGA = "Les Meilleurs Mangas Japonais En Lecture En Ligne | JapScan.Com"
SITE_TITLE_HEADER = "Lecture En Ligne Des Chapitres"
DB_CACHE = ".japscanrc"
OUTPUT = "output"

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
    print src
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

def get_manga_info(manga):
    soup, title = get_manga_html(manga)
    chapters = soup.find(id="liste_chapitres")

    vdict = {}
    if options.verbose: print "Retrieving volumes list ..."
    volumes = chapters.find_all('h2')
    vlist = []
    vlist.append("Unreleased")
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

    print "{0} has the following {1} volumes, totalizing {2} chapters".format(title, len(vlist), last_chapter)
    for v in vlist:
        print " - {0}".format(v)

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
        retrieve_manga(options.manga, options.books, options.chapters)
        sys.exit(0)
else:
    print parser.print_help()
    sys.exit(1)

# manga = options.manga
# print "Looking for {0} ...".format(manga)

# manga_url = "{0}/mangas/{1}/".format(SITE, manga)
# print manga_url
# r = requests.get(manga_url)

# soup = BeautifulSoup(r.text, "html.parser")
# title = soup.title.string
# if title == "Liste Des Mangas En Lecture En Ligne":
#     print "Manga {0} can't be found ! Aborting".format(manga)
#     sys.exit(1)

# chapters = soup.find(id="liste_chapitres")

# vdict = {}
# print "Retrieving volumes list ..."
# volumes = chapters.find_all('h2')
# vlist = []
# vlist.append("Unreleased")
# for v in volumes:
#     vlist.append(v.string)
# print vlist
# print "Retrieving chapters list ..."
# i = 0
# ul = chapters.find_all('ul')
# for c in ul:
#     chaps = []
#     for ch in c.find_all('a'):
#         chaps.append(ch.get('href').split('/')[-2])
#     print chaps
#     vdict[vlist[i]] = chaps
#     i += 1

# # print vdict

# # Create output dir
# output = "{0}/{1}".format(OUTPUT, manga)
# if not os.path.exists(output):
#     os.makedirs(output)

# for v in vlist:
#     vout = "{0}/{1}".format(output, v)
#     if not os.path.exists(vout):
#         os.makedirs(vout)

#     # Saving volumes
#     print "Retrieving pages from {0} ...".format(v)
#     ch = vdict[v]
#     for c in ch:
#         print " - Retrieving pages from chapter {0}".format(c)

#         cout = "{0}/{1}/{2}".format(output, v, c)
#         if not os.path.exists(cout):
#             os.makedirs(cout)

#         pages = get_chapter_pages (manga, c)
#         print pages

#         # Saving images
#         for p in pages:
#             img_nr = p.split('.')[0]
#             img_path = "{0}/{1}/{2}/{3}".format(output, v, c, "{0}.jpg".format(img_nr))

#             if os.path.exists(img_path):
#                 continue

#             img = get_page_image(manga, c, p)
#             print "  + Downloading image from {0}".format(img)

#             file = requests.get(img, stream=True)
#             with open(img_path, 'wb') as out_file:
#                 shutil.copyfileobj(file.raw, out_file)
#             del file

#         # Saving chapter PDF
#         pdf_path = "{0}/{1}/{2}/{2}.pdf".format(output, v, c)
#         if not os.path.exists(pdf_path):
#             print "  + Saving chapter to {0}".format(pdf_path)

#             jpgs = []
#             for p in pages:
#                 img_nr = p.split('.')[0]
#                 jpgs.append('{0}/{1}/{2}/{3}.jpg'.format(output, v, c, img_nr))

#             pdfjoin = sh.pdfjoin.bake(_tty_out=True)
#             log = pdfjoin('-o', pdf_path, '--landscape', '--rotateoversize', 'false', jpgs).stdout.strip()

#     # Saving volume to PDF
#     print "..."
