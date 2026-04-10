import os
import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
TASKS_FILE = "tasks.json"

SYSTEM_PROMPT = """Ты личный помощник и бизнес-планировщик Саида. Живёт на Южном Кипре.
Цель: заработать 4500 евро за 30 дней.
Долги: пацанам 400-500 евро СРОЧНО, штрафы ПДД 1000 евро, общие долги 2500 долларов.
К приезду девушки через 30 дней нужно 2000 евро плюс квартира и авто.
Направления:
1. Реклама девушке клининг Киев Google Ads - СРОЧНО
2. Реклама дяде Саше клининг FB плюс креативы - СРОЧНО
3. Химчистка авто 100-130 евро, мебель от 50 евро
4. Сайт химчистки на троих пацанов
5. Сайт Google аккаунтов - доделать плюс реклама
6. 20 аккаунтов в день арбитраж плюс карты плюс ссылки
7. Отчёты арбитраж каждое утро 9:30
8. Сайт для девушки - дедлайн 30 дней
Расписание: 9:00 отжимания душ завтрак, 9:30-10:00 отчёты, футбол пн и ср вечером.
Отвечай на русском. Коротко и конкретно как опытный бизнесмен."""

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "Q1": [], "Q2": [], "Q3": [], "Q4": [], "done": [],
        "earnings": 0,
        "debts": {"pacany": 450, "shtrafy": 1000, "obshie": 2500}
    }

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def main_menu():
    keyboard = [
        [InlineKeyboardButton("Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton("Срочные Q1", callback_data="view_Q1"),
         InlineKeyboardButton("Важные Q2", callback_data="view_Q2")],
        [InlineKeyboardButton("Делегировать Q3", callback_data="view_Q3"),
         InlineKeyboardButton("Потом Q4", callback_data="view_Q4")],
        [InlineKeyboardButton("Выполненные", callback_data="view_done")],
        [InlineKeyboardButton("Финансы", callback_data="finances")],
        [InlineKeyboardButton("Что делать сейчас?", callback_data="ai_advice")],
    ]
    return InlineKeyboardMarkup(keyboard)

def priority_menu():
    keyboard = [
        [InlineKeyboardButton("Срочно + Важно Q1", callback_data="prio_Q1")],
        [InlineKeyboardButton("Важно не срочно Q2", callback_data="prio_Q2")],
        [InlineKeyboardButton("Срочно не важно Q3", callback_data="prio_Q3")],
        [InlineKeyboardButton("Не срочно не важно Q4", callback_data="prio_Q4")],
        [InlineKeyboardButton("Пусть ИИ решит", callback_data="prio_AI")],
        [InlineKeyboardButton("Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def ask_claude(message, tasks=None):
    context = ""
    if tasks:
        context = f"\nЗадачи Q1={tasks.get('Q1',[])} Q2={tasks.get('Q2',[])} Заработано={tasks.get('earnings',0)} евро"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "system": SYSTEM_PROMPT + context,
                "messages": [{"role": "user", "content": message}],
            }
        )
        return r.json()["content"][0]["text"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет Саид! Я твой личный планировщик. Выбери действие:",
        reply_markup=main_menu()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    tasks = load_tasks()

    if d == "back_main":
        await q.edit_message_text("Главное меню:", reply_markup=main_menu())

    elif d == "cancel":
        context.user_data.clear()
        await q.edit_message_text("Главное меню:", reply_markup=main_menu())

    elif d == "add_task":
        context.user_data["add"] = True
        kb = [[InlineKeyboardButton("Отмена", callback_data="cancel")]]
        await q.edit_message_text("Напиши название задачи:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("prio_"):
        p = d.replace("prio_", "")
        task = context.user_data.get("task", "")
        if not task:
            await q.edit_message_text("Главное меню:", reply_markup=main_menu())
            return
        if p == "AI":
            ai = await ask_claude(f"Определи приоритет Q1 Q2 Q3 или Q4 для задачи: {task}. Ответь только одним словом Q1 Q2 Q3 или Q4.")
            p = "Q1" if "Q1" in ai else "Q2" if "Q2" in ai else "Q3" if "Q3" in ai else "Q4"
            note = f"\n\nИИ выбрал: {p}"
        else:
            note = ""
        tasks[p].append(task)
        save_tasks(tasks)
        context.user_data.clear()
        labels = {"Q1": "Срочно", "Q2": "Важно", "Q3": "Делегировать", "Q4": "Потом"}
        await q.edit_message_text(
            f"Добавлено!\n\n{task}\n{labels[p]}{note}",
            reply_markup=main_menu()
        )

    elif d.startswith("view_"):
        qd = d.replace("view_", "")
        labels = {"Q1": "Срочно", "Q2": "Важно", "Q3": "Делегировать", "Q4": "Потом", "done": "Выполненные"}
        items = tasks.get(qd, [])
        if not items:
            kb = [[InlineKeyboardButton("Назад", callback_data="back_main")]]
            await q.edit_message_text(f"{labels[qd]}\n\nПусто!", reply_markup=InlineKeyboardMarkup(kb))
            return
        kb = []
        for i, t in enumerate(items):
            short = t[:35] + "..." if len(t) > 35 else t
            kb.append([InlineKeyboardButton(short, callback_data=f"t_{qd}_{i}")])
        kb.append([InlineKeyboardButton("Назад", callback_data="back_main")])
        await q.edit_message_text(f"{labels[qd]} ({len(items)}):", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("t_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            kb = [
                [InlineKeyboardButton("Выполнено", callback_data=f"done_{qd}_{i}")],
                [InlineKeyboardButton("Удалить", callback_data=f"del_{qd}_{i}")],
                [InlineKeyboardButton("Назад", callback_data=f"view_{qd}")],
            ]
            await q.edit_message_text(items[i], reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("done_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            tasks["done"].append(name)
            save_tasks(tasks)
            await q.edit_message_text(f"Выполнено: {name}", reply_markup=main_menu())

    elif d.startswith("del_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            save_tasks(tasks)
            await q.edit_message_text(f"Удалено: {name}", reply_markup=main_menu())

    elif d == "finances":
        earned = tasks.get("earnings", 0)
        goal = 4500
        pct = int((earned / goal) * 100) if goal > 0 else 0
        bar = "X" * (pct // 10) + "." * (10 - pct // 10)
        debts = tasks.get("debts", {})
        msg = f"ФИНАНСЫ\n\n{bar} {pct}%\nЗаработано: {earned} / {goal} евро\nОсталось: {goal - earned} евро\n\nДолги:\nПацаны: {debts.get('pacany', 450)} евро\nШтрафы: {debts.get('shtrafy', 1000)} евро\nОбщие: {debts.get('obshie', 2500)} долларов"
        kb = [
            [InlineKeyboardButton("Добавить доход", callback_data="income")],
            [InlineKeyboardButton("Назад", callback_data="back_main")],
        ]
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))

    elif d == "income":
        context.user_data["income"] = True
        kb = [[InlineKeyboardButton("Отмена", callback_data="cancel")]]
        await q.edit_message_text("Сколько заработал? Напиши сумму в евро:", reply_markup=InlineKeyboardMarkup(kb))

    elif d == "ai_advice":
        await q.edit_message_text("Думаю...")
        advice = await ask_claude("Что мне делать прямо сейчас? Дай конкретный план на сегодня по часам.", tasks)
        kb = [[InlineKeyboardButton("Назад", callback_data="back_main")]]
        await q.edit_message_text(advice, reply_markup=InlineKeyboardMarkup(kb))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tasks = load_tasks()

    if context.user_data.get("add"):
        context.user_data["task"] = text
        context.user_data["add"] = False
        await update.message.reply_text(
            f"Задача: {text}\n\nКакой приоритет?",
            reply_markup=priority_menu()
        )
    elif context.user_data.get("income"):
        context.user_data.clear()
        try:
            amount = float(''.join(c for c in text if c.isdigit() or c == '.'))
            tasks["earnings"] = tasks.get("earnings", 0) + amount
            save_tasks(tasks)
            pct = int((tasks["earnings"] / 4500) * 100)
            await update.message.reply_text(
                f"Добавлено: +{amount} евро\nИтого: {tasks['earnings']} евро\nПрогресс: {pct}%",
                reply_markup=main_menu()
            )
        except:
            await update.message.reply_text("Не понял сумму.", reply_markup=main_menu())
    else:
        response = await ask_claude(text, tasks)
        kb = [[InlineKeyboardButton("Меню", callback_data="back_main")]]
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
