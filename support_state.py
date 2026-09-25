"""
Состояние заявок в поддержку (/support).

Пользователь пишет /support -> ждём его следующее сообщение (любого типа) ->
пересылаем администратору в ЛС -> администратор отвечает Reply на это
пересланное сообщение прямо в своём чате с ботом -> ответ уходит обратно
пользователю.

Всё хранится в памяти (переживает рестарт бота хуже, чем БД, но заявки в
поддержку живут недолго — это ок, как и другие "pending"-состояния в
проекте, см. picker_state.py/gift_states.py).
"""
import time
from typing import Dict

# uid -> ts: пользователь только что вызвал /support, ждём его сообщение
waiting_support_message: Dict[int, float] = {}

# message_id (в чате администратора) -> {"uid": int, "label": str}
# нужно, чтобы Reply админа на пересланное сообщение можно было доставить
# обратно нужному пользователю.
support_tickets: Dict[int, dict] = {}

TICKET_TTL_SEC = 7 * 24 * 3600  # неделя — дольше отвечать на заявку не имеет смысла


def cleanup() -> None:
    now = time.time()
    for uid, ts in list(waiting_support_message.items()):
        if now - ts > 600:
            waiting_support_message.pop(uid, None)
    for msg_id, rec in list(support_tickets.items()):
        if now - rec.get("ts", 0) > TICKET_TTL_SEC:
            support_tickets.pop(msg_id, None)
