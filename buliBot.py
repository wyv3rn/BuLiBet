#!/usr/bin/env python3

import logging as log
import sys
import argparse
import re
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from tinydb import TinyDB, Query

from match import *
from commands import *
from buttons import *
import db

# TODO log to file as well
log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=log.INFO)

def main(token, storage):
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    log.log(log.INFO, 'Bot controller started')

    # load database and other global init
    db.init(storage)

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('bet', bet, pass_args=True))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    log.log(log.INFO, 'Starting to poll ...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('token', help='Token for telegram bot API')
    parser.add_argument('--storage', default='db/', help='Storage directory for the databasa (default: ./db/')
    args = parser.parse_args()
    main(args.token, args.storage)

