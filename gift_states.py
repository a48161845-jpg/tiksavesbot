"""
FSM (Finite State Machine) для процесса покупки подарков:
- GiftBuyStates.enter_recipient — ввод ID/username получателя
- GiftBuyStates.enter_comment — ввод комментария (опционально)
"""
from aiogram.fsm.state import State, StatesGroup


class GiftBuyStates(StatesGroup):
    """Состояния при покупке подарка за звёзды другому пользователю."""
    enter_recipient = State()  # Ввод ID или @username получателя
    enter_comment = State()    # Ввод комментария (опционально)
