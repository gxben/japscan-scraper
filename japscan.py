#!/usr/bin/env python2.7

import sys, os
import shutil
import sh
import requests
from bs4 import BeautifulSoup

SITE = "http://www.japscan.com"
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

# use UTF-8 encoding instead of unicode to support more characters
reload(sys)
sys.setdefaultencoding("utf-8")

if len(sys.argv) < 2:
    print "japscan.py [manga]"
    sys.exit(1)

manga = sys.argv[1]
print "Looking for {0} ...".format(manga)

manga_url = "{0}/mangas/{1}/".format(SITE, manga)
print manga_url
r = requests.get(manga_url)

soup = BeautifulSoup(r.text, "html.parser")
title = soup.title.string
if title == "Liste Des Mangas En Lecture En Ligne":
    print "Manga {0} can't be found ! Aborting".format(manga)
    sys.exit(1)

chapters = soup.find(id="liste_chapitres")

vdict = {}
print "Retrieving volumes list ..."
volumes = chapters.find_all('h2')
vlist = []
vlist.append("Unreleased")
for v in volumes:
    vlist.append(v.string)
print vlist
print "Retrieving chapters list ..."
i = 0
ul = chapters.find_all('ul')
for c in ul:
    chaps = []
    for ch in c.find_all('a'):
        chaps.append(ch.get('href').split('/')[-2])
    print chaps
    vdict[vlist[i]] = chaps
    i += 1

# print vdict

# Create output dir
output = "{0}/{1}".format(OUTPUT, manga)
if not os.path.exists(output):
    os.makedirs(output)

for v in vlist:
    vout = "{0}/{1}".format(output, v)
    if not os.path.exists(vout):
        os.makedirs(vout)

    # Saving volumes
    print "Retrieving pages from {0} ...".format(v)
    ch = vdict[v]
    for c in ch:
        print " - Retrieving pages from chapter {0}".format(c)

        cout = "{0}/{1}/{2}".format(output, v, c)
        if not os.path.exists(cout):
            os.makedirs(cout)

        pages = get_chapter_pages (manga, c)
        print pages

        # Saving images
        for p in pages:
            img_nr = p.split('.')[0]
            img_path = "{0}/{1}/{2}/{3}".format(output, v, c, "{0}.jpg".format(img_nr))

            if os.path.exists(img_path):
                continue

            img = get_page_image(manga, c, p)
            print "  + Downloading image from {0}".format(img)

            file = requests.get(img, stream=True)
            with open(img_path, 'wb') as out_file:
                shutil.copyfileobj(file.raw, out_file)
            del file

        # Saving chapter PDF
        pdf_path = "{0}/{1}/{2}/{2}.pdf".format(output, v, c)
        if not os.path.exists(pdf_path):
            print "  + Saving chapter to {0}".format(pdf_path)

            jpgs = []
            for p in pages:
                img_nr = p.split('.')[0]
                jpgs.append('{0}/{1}/{2}/{3}.jpg'.format(output, v, c, img_nr))

            pdfjoin = sh.pdfjoin.bake(_tty_out=True)
            log = pdfjoin('-o', pdf_path, '--landscape', '--rotateoversize', 'false', jpgs).stdout.strip()

    # Saving volume to PDF
    print "..."
