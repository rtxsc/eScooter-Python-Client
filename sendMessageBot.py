#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram import InlineQueryResultArticle, InputTextMessageContent
import logging
import requests
import telegram


bot = telegram.Bot(token='1242269165:AAHDaelCeHjZBAvFyOxHrgXjwo2SxYzT1PY')
print(bot.get_me())

updater = Updater(token='1242269165:AAHDaelCeHjZBAvFyOxHrgXjwo2SxYzT1PY', use_context=True)
dispatcher = updater.dispatcher


def telegram_bot_sendtext(bot_message):

    bot_token = '1242269165:AAHDaelCeHjZBAvFyOxHrgXjwo2SxYzT1PY'
    bot_chatID = '662382293'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()


def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Caps',
            input_message_content=InputTextMessageContent(query.upper())
        )
    )
    context.bot.answer_inline_query(update.inline_query.id, results)

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

def getLocation(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="My current location is:{}")

def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

caps_handler = CommandHandler('caps', caps)
start_handler = CommandHandler('start', start)
start_handler2 = CommandHandler('location', getLocation)
echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
inline_caps_handler = InlineQueryHandler(inline_caps)
unknown_handler = MessageHandler(Filters.command, unknown)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(start_handler2)
dispatcher.add_handler(echo_handler)
dispatcher.add_handler(caps_handler)
dispatcher.add_handler(inline_caps_handler)
dispatcher.add_handler(unknown_handler)
test = telegram_bot_sendtext("client-s1 is activated!")
print("Testing Bot: {}".format(test))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
updater.start_polling()
