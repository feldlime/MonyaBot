import re
import traceback
from collections import defaultdict
from functools import partial

from aiogram import types as tt, Dispatcher
from aiogram.utils.callback_data import CallbackData

from monya.db import DBService, ChatAlreadyExistsError, UserAlreadyExistsError, \
    UserNotExistsError
from monya.log import app_logger
import typing as tp

from monya.settings import ServiceConfig

CHAT = "__chat__"

user_cb = CallbackData("user", "cb_type", "name")
status_cb = CallbackData("status", "variant")


def make_op_users_kb(
    op: str,
    users: tp.Sequence[str],
) -> tt.InlineKeyboardMarkup:
    buttons = [
        tt.InlineKeyboardButton(
            user,
            switch_inline_query_current_chat=f"{op} {user} "
        )
        for user in users
    ]
    keyboard = tt.InlineKeyboardMarkup(row_width=2).add(*buttons)
    return keyboard


def make_chat_and_users_kb(
    cb_type: str,
    users: tp.Sequence[str],
) -> tt.InlineKeyboardMarkup:
    chat_button = tt.InlineKeyboardButton(
        "Все",
        callback_data=user_cb.new(cb_type=cb_type, name=CHAT),
    )
    user_buttons = [
        tt.InlineKeyboardButton(
            user,
            callback_data=user_cb.new(cb_type=cb_type, name=user),
        )
        for user in users
    ]

    keyboard = (
        tt.InlineKeyboardMarkup(row_width=2)
        .row(chat_button)
        .add(*user_buttons)
    )
    return keyboard


async def handle(handler, db_service, event: tt.Message):
    try:
        await db_service.add_chat(event.chat.id)
    except ChatAlreadyExistsError:
        pass
    try:
        await handler(event, db_service)
    except Exception:
        app_logger.error(traceback.format_exc())
        raise


async def handle_cb(
    handler,
    db_service,
    query: tt.CallbackQuery,
    callback_data: tp.Dict[str, str],
):
    try:
        await handler(query, callback_data, db_service)
    except Exception:
        app_logger.error(traceback.format_exc())
        raise


async def start_h(event: tt.Message, db_service: DBService) -> None:
    reply = (
        "Привет! Я Моня - бот для контроля трат в компании.\n"
        "Добавьте участников мероприятия, потом сообщайте, "
        "кто сколько дал (push) и взял (pull), а я подведу итог.\n"
        "Наберите /help для вывода списка команд"
    )
    await event.reply(reply)


async def help_h(event: tt.Message, db_service: DBService) -> None:
    reply = (
        """
        Вот что я умею:
/add Имя - добавить участника
/delete Имя - удалить участника (вместе с его историей!)
/reset - удалить всю историю в чате (участники не удалятся)
/users - получить список текущих участников
/pay - записать оплату
/spend - записать трату
/history - показать историю операций и баланс
/status - показать статус
        """
    )
    await event.reply(reply)


async def reset_h(event: tt.Message, db_service: DBService) -> None:
    expected = "/reset Подтверждаю"
    if event.text != expected:
        reply = f"Напишите '{expected}', если точно хотите все сбросить"
    else:
        await db_service.reset(event.chat.id)
        reply = "Ба-бах... сброшено"
    await event.reply(reply)


async def add_user_h(event: tt.Message, db_service: DBService) -> None:
    if not re.match(r"^/add\s+\w+\s*$", event.text):
        reply = "Что-то не то: нужно писать '/add Имя'"
    else:
        name = event.text.split()[1].strip()
        try:
            await db_service.add_user(event.chat.id, name)
        except UserAlreadyExistsError:
            reply = f"Ошибка: {name} уже есть - двоих взять не можем :("
        else:
            reply = f"Готово: {name} теперь с нами!"

    await event.reply(reply)


async def delete_user_h(event: tt.Message, db_service: DBService) -> None:
    if not re.match(r"^/delete\s+\w+\s*$", event.text):
        reply = "Что-то не то - нужно писать '/delete Имя'"
    else:
        name = event.text.split()[1].strip()
        try:
            await db_service.delete_user(event.chat.id, name)
        except UserNotExistsError:
            reply = f"Ошибка: {name} отсутствует в списке"
        else:
            reply = f"Готово: {name} больше не с нами"

    await event.reply(reply)


async def get_users_h(event: tt.Message, db_service: DBService) -> None:
    users = await db_service.get_chat_users(event.chat.id)
    users_str = ", ".join(users) if users else "никого нет"
    reply = f"У нас здесь: {users_str}"
    await event.reply(reply)


async def pay_h(event: tt.Message, db_service: DBService) -> None:
    users = await db_service.get_chat_users(event.chat.id)
    keyboard = make_op_users_kb("pay", users)
    reply = (
        "Кто заплатил? "
        "Добавьте к сообщению сумму и комментарий (если нужно)"
    )
    await event.reply(reply, reply_markup=keyboard)


async def spend_h(event: tt.Message, db_service: DBService) -> None:
    users = await db_service.get_chat_users(event.chat.id)
    keyboard = make_op_users_kb("spend", users)
    reply = (
        "Кто потратил? "
        "Добавьте к сообщению сумму и комментарий (если нужно)"
    )
    await event.reply(reply, reply_markup=keyboard)


async def spend_pay_msg_h(event: tt.Message, db_service: DBService) -> None:
    _, cmd, name, amount, *comments = event.text.split(maxsplit=4)
    comment = " ".join(comments)
    amount = float(amount.replace(",", "."))
    assert cmd in ("pay", "spend")
    if cmd == "spend":
        amount = -amount
    await db_service.add_operation(event.chat.id, name, amount, comment)
    reply = f"Записано: {name} {amount:+.0f} руб."
    if comment:
        reply += f" '{comment}'"
    await event.reply(reply)


async def get_history_h(event: tt.Message, db_service: DBService) -> None:
    users = await db_service.get_chat_users(event.chat.id)
    keyboard = make_chat_and_users_kb("history", users)
    reply = "По кому показать историю?"
    await event.reply(reply, reply_markup=keyboard)


async def get_history_cb_h(
    query: tt.CallbackQuery,
    callback_data: tp.Dict[str, str],
    db_service: DBService,
) -> None:
    await query.answer()
    user = callback_data["name"]

    chat_id = query.message.chat.id
    if user == CHAT:
        hist = await db_service.get_chat_operations(chat_id)
        balance = sum([r[1] for r in hist])
        reply = "\n".join([f"- {nm} {am:+.0f} '{cm}'" for nm, am, cm in hist])
    else:
        hist = await db_service.get_user_operations(chat_id, user)
        balance = sum([r[0] for r in hist])
        reply = f"Итак, {user}\n"
        reply += "\n".join([f"{am:+.0f} '{cm}'" for am, cm in hist])
    reply += f"\n\nБаланс: {balance:+.0f} руб."
    await query.bot.send_message(
        chat_id,
        reply,
    )


def calc_grouped_amounts(history):
    grouped = defaultdict(int)
    for action in history:
        name = action[0]
        amount = action[1]
        grouped[name] += amount
    return dict(grouped)


def format_status_reply(statuses: tp.Dict[str, float]):
    rows = []
    for user, amount in statuses.items():
        if amount > 0:
            rows.append(f"- {user}  <--  {amount:.0f} руб.")
        elif amount < 0:
            rows.append(f"- {user}  -->  {-amount:.0f} руб.")
        else:
            rows.append(f"- {user} в расчете")
    return "\n".join(rows)


async def get_status_h(event: tt.Message, db_service: DBService) -> None:
    history = await db_service.get_chat_operations(event.chat.id)
    rest = sum([r[1] for r in history])

    if rest < 1:
        grouped = calc_grouped_amounts(history)
        reply = "В итоге имеем:\n" + format_status_reply(grouped)
        if rest < -1:
            reply = (
                f"Внимание! Отрицательный баланс: {rest} руб. "
                f"- кто-то не записал пополнение.\n\n"
                + reply
            )
        await event.reply(reply)
        return

    reply = f"В котле осталось {rest:.0f} руб. Что сделать?"
    keyboard = tt.InlineKeyboardMarkup().row(
        tt.InlineKeyboardButton(
            "Вернуть тем, кто положил",
            callback_data=status_cb.new(variant="return"),
        ),
        tt.InlineKeyboardButton(
            "Распределить поровну",
            callback_data=status_cb.new(variant="divide"),
        )
    )
    await event.reply(reply, reply_markup=keyboard)


async def get_statuses_cb_h(
    query: tt.CallbackQuery,
    callback_data: tp.Dict[str, str],
    db_service: DBService,
) -> None:
    await query.answer()
    history = await db_service.get_chat_operations(query.message.chat.id)
    statuses = calc_grouped_amounts(history)

    variant = callback_data["variant"]
    if variant == "divide":
        users = await db_service.get_chat_users(query.message.chat.id)
        rest = sum(statuses.values()) / len(users)
        statuses = {name: amount - rest for name, amount in statuses.items()}
        reply = "Разделив остаток поровну, получим:\n"
    else:
        reply = "Вернув остаток вкладчикам, получим:\n"

    reply += format_status_reply(statuses)
    await query.bot.send_message(query.message.chat.id, reply)


async def other_msg_h(event: tt.Message, db_service: DBService) -> None:
    reply = f"Что-то я вас не пойму, выражайтесь яснее!"
    await event.reply(reply)


def add_handlers(
    dp: Dispatcher,
    db_service: DBService,
    config: ServiceConfig,
) -> None:
    dp.register_message_handler(
        partial(handle, start_h, db_service),
        commands={"start"},
    )
    dp.register_message_handler(
        partial(handle, help_h, db_service),
        commands={"help"},
    )
    dp.register_message_handler(
        partial(handle, reset_h, db_service),
        commands={"reset"},
    )
    dp.register_message_handler(
        partial(handle, add_user_h, db_service),
        commands={"add"},
    )
    dp.register_message_handler(
        partial(handle, delete_user_h, db_service),
        commands={"delete"},
    )
    dp.register_message_handler(
        partial(handle, get_users_h, db_service),
        commands={"users"},
    )
    dp.register_message_handler(
        partial(handle, pay_h, db_service),
        commands={"pay"},
    )
    dp.register_message_handler(
        partial(handle, spend_h, db_service),
        commands={"spend"},
    )
    bot_name = config.telegram_config.bot_name
    dp.register_message_handler(
        partial(handle, spend_pay_msg_h, db_service),
        regexp=fr"^@{bot_name}\s+(pay|spend)\s+\w+\s+\d+((\.|,)\d+)?.*$",
    )
    dp.register_message_handler(
        partial(handle, get_history_h, db_service),
        commands={"history"},
    )
    dp.register_callback_query_handler(
        partial(handle_cb, get_history_cb_h, db_service),
        user_cb.filter(cb_type="history"),
    )
    dp.register_message_handler(
        partial(handle, get_status_h, db_service),
        commands={"status"},
    )
    dp.register_callback_query_handler(
        partial(handle_cb, get_statuses_cb_h, db_service),
        status_cb.filter(variant=["return", "divide"]),
    )
    dp.register_message_handler(
        partial(handle, other_msg_h, db_service),
        regexp=fr"@{bot_name}",
    )
