

import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from aiogram.filters import Command
from aiogram.utils.formatting import (
    Bold, as_list, as_marked_section, as_key_value
)
from bot import Bot_q

logging.basicConfig(level=logging.INFO)
API_TOKEN = '7809947591:AAH1oTYAXnXaKFyXeFTFGzsx3FIkjk02iTY'
quiz_bot = Bot_q(token=API_TOKEN)
quiz_data = quiz_bot.data['quiz_data']
user_ans = {}


def generate_options_keyboard(answer_options, right):
    builder = InlineKeyboardBuilder()

    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"{option}:{'right' if option == right else 'wrong'}")
        )

    builder.adjust(1)
    return builder.as_markup()


@quiz_bot.dp.message(F.text == 'Результат')
async def test_result(message: types.Message):
    num_q = []
    answer = []
    result = []
    for i in user_ans:
        num_q.append(i)
        answer.append(list(user_ans[i])[0])
        result.append(list(user_ans[i].values())[0])
    correct_answer = [(index + 1, ans) for index, (ans, status) in enumerate(zip(answer, result)) if status == 'right']
    formatted_answers = "\n\n".join(f"{index} ✅ :{ans}" for index, ans in correct_answer)

    wrong_answer = [(index + 1, ans) for index, (ans, status) in enumerate(zip(answer, result)) if status == 'wrong']
    formatted_answers_wrong = "\n\n".join(f"{index} ❌:{ans}" for index, ans in wrong_answer)
    content = as_list(
        as_marked_section(Bold("Success:"), formatted_answers, marker=""),
        as_marked_section(Bold("Failed:"), formatted_answers_wrong, marker=""),
        as_marked_section(
            Bold("Summary:"),
            as_key_value("Total", (len(num_q))),
            as_key_value("Success", (len(correct_answer))),
            as_key_value("Failed", (len(wrong_answer))),
            marker="  ",
        ),
    )
    await message.answer(**content.as_kwargs())


@quiz_bot.dp.callback_query()
async def handle_answer(callback: types.CallbackQuery):
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']
    user_answer, result = callback.data.split(':')
    if result == 'right':
        user_ans[current_question_index] = {user_answer:result}
        response_text = f"Верно! Вы выбрали: {user_answer}"
        await callback.message.answer(response_text)
    else:
        user_ans[current_question_index] = {user_answer:result}
        response_text = f"Неправильно! Вы выбрали: {user_answer}"
        await callback.message.answer(response_text)
        await callback.message.answer(
            f"Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")
    await send_question(callback=callback)


async def send_question(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    current_question_index = await get_quiz_index(callback.from_user.id)
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


# Хэндлер на команду /start
@quiz_bot.dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


async def get_question(message, user_id):
    # Получение текущего вопроса из словаря состояний пользователя
    current_question_index = await get_quiz_index(user_id)
    question_data = quiz_data[current_question_index]
    # Генерация кнопок для текущего вопроса
    answer_options = quiz_data[current_question_index]['options']
    right_answer = question_data['correct_option']
    keyboard = generate_options_keyboard(answer_options, answer_options[right_answer])

    # Отправка вопроса с кнопками
    await message.answer(question_data['question'], reply_markup=keyboard)


async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)
    await get_question(message, user_id)


async def get_quiz_index(user_id):
    # Подключаемся к базе данных
    async with aiosqlite.connect(quiz_bot.DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(quiz_bot.DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        # Сохраняем изменения
        await db.commit()


# Хэндлер на команду /quiz
@quiz_bot.dp.message(F.text == "Начать игру")
@quiz_bot.dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)


async def create_table():
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(quiz_bot.DB_NAME) as db:
        # Создаем таблицу
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')
        # Сохраняем изменения
        await db.commit()


# Запуск процесса поллинга новых апдейтов
async def main():
    # Запускаем создание таблицы базы данных
    await create_table()

    await quiz_bot.dp.start_polling(quiz_bot)


if __name__ == "__main__":
    asyncio.run(main())
