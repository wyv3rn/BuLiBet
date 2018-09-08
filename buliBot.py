#!/usr/bin/env python3

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import logging as log
import time
import sys
import argparse

log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=log.INFO)


class Match:
    def __init__(self, home, guest):
        self.home = home
        self.guest = guest
        self.home_score = 0
        self.guest_score = 0

    def inc_home_score(self):
        self.home_score += 1

    def dec_home_score(self):
        if self.home_score > 0:
            self.home_score -= 1

    def inc_guest_score(self):
        self.guest_score += 1

    def dec_guest_score(self):
        if self.guest_score > 0:
            self.guest_score -= 1

    def to_buttons(self, row):
        buttons = [InlineKeyboardButton('-', callback_data='{} -home'.format(row)),
                    InlineKeyboardButton(self.home, callback_data='{} +home'.format(row)),
                    InlineKeyboardButton('{} : {}'.format(self.home_score, self.guest_score), callback_data='{} nop'.format(row)),
                    InlineKeyboardButton(self.guest, callback_data='{} +guest'.format(row)),
                    InlineKeyboardButton('-', callback_data='{} -guest'.format(row))]
        return buttons

def matches_to_keyboard(matches):
    keyboard = []
    for i in range(len(matches)):
        keyboard.append(matches[i].to_buttons(i))
    keyboard.append([InlineKeyboardButton('Done 🙈', callback_data='done')])
    return keyboard


def start(bot, update):
    log.log(log.INFO, 'Received start command message {}'.format(update.message))
    bot.send_message(chat_id=update.message.chat_id, text='You wanna start? But I\'m not ready yet :(')

def key(bot, update):
    global matches
    match0 = Match('FCB', 'FCN')
    match1 = Match('BVB', 'S04')
    matches = [match0, match1]

    reply_markup = InlineKeyboardMarkup(matches_to_keyboard(matches))
    update.message.reply_text('Here we go:', reply_markup=reply_markup)

def button(bot, update):
    global matches
    query = update.callback_query

    if query.data == 'done':
        bot.edit_message_text(chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        text='Done!')
        return

    row, command = query.data.split(' ')
    row = int(row)
    if command == 'nop':
        return
    elif command == '+home':
        matches[row].inc_home_score()
    elif command == '-home':
        matches[row].dec_home_score()
    elif command == '+guest':
        matches[row].inc_guest_score()
    elif command == '-guest':
        matches[row].dec_guest_score()
    else:
        assert False, 'Unexpected button callback {}'.format(command)

    reply_markup = InlineKeyboardMarkup(matches_to_keyboard(matches))

    bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup)


    def main(token, storage):
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    log.log(log.INFO, 'Bot controller started')

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('key', key))
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

