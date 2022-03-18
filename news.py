import json
import codecs
import requests
from bs4 import BeautifulSoup, SoupStrainer
import telegram
from telegram import *
from telegram.ext import *

NEWS_TOKEN = '55300a48e8ca229c7ec4a11fea16fa184e8c3c7f'
def news(update, context):
    #Returns the latest news when /news is invoked.
    url = "https://cryptopanic.com/api/v1/posts/?auth_token="+NEWS_TOKEN+"&kind=news"
    mes = update.message.text.split(" ")
    if len(mes) == 1:
        message = "*Trending News*\n\n"
    elif len(mes) == 2:
        url+= "&filter=rising&currencies=" + mes[1]
        message = "*Trending " + mes[1].upper() + " News*\n\n"
    elif len(mes) == 3:
        url+= "&currencies=" + mes[1]
        url+= "&filter=" + mes[2]
        message = "*" + mes[2].title() + " " + mes[1].upper() + " News*\n\n"
    test = requests.get(url)
    dump = json.loads(test.content)
    c=0
    if dump['results']!=[]:
        for i in dump['results']:
            if c>5:
                break
            c+=1
            message+=str(c)+". ["+i['title']+"]("+i['url']+")\n\n" 
    else:
        message+="\n"
    context.bot.sendMessage(chat_id = update.message.chat_id, text = message, parse_mode='markdown',disable_web_page_preview=True)
