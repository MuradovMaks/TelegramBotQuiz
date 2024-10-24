import json

from aiogram import Bot, Dispatcher


class Bot_q(Bot):
    def __init__(self, token, **kwargs):
        super().__init__(token, **kwargs)
        with open('../TelegramBotQuiz/quiz_data.json', 'r', encoding='UTF-8') as f:
            quiz_data = json.load(f)

        self.data = quiz_data
        self.dp = Dispatcher()
        self.DB_NAME = 'quiz_bot.db'
