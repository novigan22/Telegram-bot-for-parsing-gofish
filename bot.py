import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import add_link_to_db, get_user_links, delete_link_from_db

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "YOUR_TOKEN_BOT"
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


class AddLinkStates(StatesGroup):
    waiting_for_link = State()


def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить", callback_data="add_link"),
            InlineKeyboardButton(text="Мои ссылки", callback_data="my_links")
        ]
    ])
    return keyboard


def get_cancel_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
    ])
    return keyboard


def get_links_menu(user_id: int):
    links = get_user_links(user_id)
    buttons = []
    for link_obj in links:
        display_text = link_obj.link[:30] + "..." if len(link_obj.link) > 30 else link_obj.link
        buttons.append([InlineKeyboardButton(
            text=display_text, 
            callback_data=f"link_{link_obj.id}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_delete_button(link_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить🗑️", callback_data=f"delete_{link_id}")]
    ])
    return keyboard


@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "Добро пожаловать в бота! Он поможет тебе отслеживать наличие товаров "
        "в GoFish по определенным фильтрам по твоей ссылке. Можешь добавить ссылку, "
        "посмотреть весь список или удалить ссылку (в списке твоих ссылок) "
        "благодаря меню ниже👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())


@router.callback_query(F.data == "add_link")
async def add_link_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Отправь мне ссылку с GoFish, чтобы я мог отслеживать наличие товаров по ней",
        reply_markup=get_cancel_button()
    )
    await state.set_state(AddLinkStates.waiting_for_link)
    await callback.answer()


@router.callback_query(F.data == "cancel", StateFilter(AddLinkStates.waiting_for_link))
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌Отменено")
    await state.clear()
    await callback.answer()


@router.message(StateFilter(AddLinkStates.waiting_for_link))
async def receive_link(message: Message, state: FSMContext):
    link = message.text.strip()
    add_link_to_db(message.from_user.id, link)
    await message.answer("Ссылка успешно добавлена!✅")
    await state.clear()


@router.callback_query(F.data == "my_links")
async def my_links_handler(callback: CallbackQuery):
    user_links = get_user_links(callback.from_user.id)
    
    if not user_links:
        await callback.message.edit_text("У тебя пока нет сохраненных ссылок")
    else:
        await callback.message.edit_text(
            "Вот список всех твоих ссылок👇",
            reply_markup=get_links_menu(callback.from_user.id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("link_"))
async def link_selected(callback: CallbackQuery):
    link_id = int(callback.data.split("_")[1])
    
    await callback.message.edit_text(
        "Ты уверен, что хочешь удалить эту ссылку?🔗",
        reply_markup=get_delete_button(link_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_"))
async def delete_link(callback: CallbackQuery):
    link_id = int(callback.data.split("_")[1])
    delete_link_from_db(link_id)
    await callback.message.edit_text("Ссылка удалена")
    await callback.answer()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())