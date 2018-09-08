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

    def to_buttons(self, row):
        buttons = [InlineKeyboardButton('-', callback_data='{} -home'.format(row)),
                    InlineKeyboardButton(self.home, callback_data='{} +home'.format(row)),
                    InlineKeyboardButton('{} : {}'.format(self.home_score, self.guest_score), callback_data='nop'.format(row)),
                    InlineKeyboardButton(self.guest, callback_data='{} +guest'.format(row)),
                    InlineKeyboardButton('-', callback_data='{} -guest'.format(row))]
        return buttons


def matchday_to_keyboard(matchday):
    keyboard = []
    for i in range(len(matchday)):
        keyboard.append(matchday[i].to_buttons(i))
    keyboard.append([InlineKeyboardButton('Done 🙈', callback_data='done')])
    return keyboard


def start(bot, update):
    log.log(log.INFO, 'Received start command message {}'.format(update.message))
    bot.send_message(chat_id=update.message.chat_id, text='You wanna start? But I\'m not ready yet :(')


def key(bot, update):
    global matchday
    match0 = Match('FCB', 'FCN')
    match1 = Match('BVB', 'S04')
    matchday = [match0, match1]

    reply_markup = InlineKeyboardMarkup(matchday_to_keyboard(matchday))
    update.message.reply_text('Here we go:', reply_markup=reply_markup)


def button(bot, update):
    global matchday
    query = update.callback_query

    if query.data == 'nop':
        return

    if query.data == 'done':
        bot.edit_message_text(chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        text='Done!')
        return

    row, command = query.data.split(' ')
    match = matchday[int(row)]
    if command == '+home':
        match.home_score += 1
    elif command == '-home':
        if match.home_score > 0:
            match.home_score -= 1
        else:
            return
    elif command == '+guest':
        match.guest_score += 1
    elif command == '-guest':
        if match.guest_score > 0:
            match.guest_score -= 1
        else:
            return
    else:
        assert False, 'Unexpected button callback {}'.format(command)

    reply_markup = InlineKeyboardMarkup(matchday_to_keyboard(matchday))

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

