import os
import json
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

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
Отвечай на русском. Коротко и конкретно как опытный бизнесмен.
Используй эмодзи для структуры. Выделяй главное."""

DAYS_RU = {
    "Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
    "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"
}

def get_day_ru():
    return DAYS_RU.get(datetime.now().strftime("%A"), "")

def progress_bar(current, total, length=10):
    filled = int((current / total) * length) if total > 0 else 0
    bar = "▓" * filled + "░" * (length - filled)
    pct = int((current / total) * 100) if total > 0 else 0
    return bar, pct

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
    tasks = load_tasks()
    q1 = len(tasks.get("Q1", []))
    q2 = len(tasks.get("Q2", []))
    q3 = len(tasks.get("Q3", []))
    q4 = len(tasks.get("Q4", []))
    keyboard = [
        [InlineKeyboardButton("➕  Добавить задачу", callback_data="add_task")],
        [
            InlineKeyboardButton(f"🔴  Срочные ({q1})", callback_data="view_Q1"),
            InlineKeyboardButton(f"🔵  Важные ({q2})", callback_data="view_Q2"),
        ],
        [
            InlineKeyboardButton(f"🟡  Делегировать ({q3})", callback_data="view_Q3"),
            InlineKeyboardButton(f"🟢  Потом ({q4})", callback_data="view_Q4"),
        ],
        [InlineKeyboardButton("✅  Выполненные", callback_data="view_done")],
        [InlineKeyboardButton("💰  Финансы и долги", callback_data="finances")],
        [InlineKeyboardButton("🤖  Что делать сейчас?", callback_data="ai_advice")],
    ]
    return InlineKeyboardMarkup(keyboard)

def priority_menu():
    keyboard = [
        [InlineKeyboardButton("🔴  Срочно + Важно", callback_data="prio_Q1")],
        [InlineKeyboardButton("🔵  Важно, не срочно", callback_data="prio_Q2")],
        [InlineKeyboardButton("🟡  Срочно, не важно", callback_data="prio_Q3")],
        [InlineKeyboardButton("🟢  Не срочно, не важно", callback_data="prio_Q4")],
        [InlineKeyboardButton("🤖  Пусть ИИ решит", callback_data="prio_AI")],
        [InlineKeyboardButton("❌  Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_btn(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️  Назад", callback_data=target)]])

async def ask_claude(message, tasks=None):
    now = datetime.now()
    context = f"\nСейчас: {get_day_ru()}, {now.strftime('%H:%M')}"
    if tasks:
        context += f"\nЗадачи Q1={tasks.get('Q1',[])} Q2={tasks.get('Q2',[])} Заработано={tasks.get('earnings',0)} евро"
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
                "max_tokens": 600,
                "system": SYSTEM_PROMPT + context,
                "messages": [{"role": "user", "content": message}],
            }
        )
        return r.json()["content"][0]["text"]

def welcome_text():
    tasks = load_tasks()
    now = datetime.now()
    day = get_day_ru()
    earned = tasks.get("earnings", 0)
    bar, pct = progress_bar(earned, 4500)
    q1 = len(tasks.get("Q1", []))
    total_active = sum(len(tasks.get(q, [])) for q in ["Q1","Q2","Q3","Q4"])
    done = len(tasks.get("done", []))

    text = f"""👋 *Привет, Саид!*

📅 {day} · {now.strftime('%H:%M')}

━━━━━━━━━━━━━━━
💰 *Прогресс к цели*
{bar} *{pct}%*
_{earned}€ из 4500€_

━━━━━━━━━━━━━━━
📋 *Задачи*
🔴 Срочных: *{q1}*
📌 Всего активных: *{total_active}*
✅ Выполнено: *{done}*

━━━━━━━━━━━━━━━
_Выбери действие:_"""
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        welcome_text(),
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    tasks = load_tasks()

    if d == "back_main":
        await q.edit_message_text(welcome_text(), reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

    elif d == "cancel":
        context.user_data.clear()
        await q.edit_message_text(welcome_text(), reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

    elif d == "add_task":
        context.user_data["add"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await q.edit_message_text(
            "✏️ *Новая задача*\n\nНапиши название задачи:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif d.startswith("prio_"):
        p = d.replace("prio_", "")
        task = context.user_data.get("task", "")
        if not task:
            await q.edit_message_text(welcome_text(), reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)
            return
        if p == "AI":
            ai = await ask_claude(f"Определи приоритет Q1 Q2 Q3 или Q4 для задачи: {task}. Ответь только Q1, Q2, Q3 или Q4.")
            p = "Q1" if "Q1" in ai else "Q2" if "Q2" in ai else "Q3" if "Q3" in ai else "Q4"
            note = f"\n\n🤖 _ИИ определил приоритет: {p}_"
        else:
            note = ""
        tasks[p].append(task)
        save_tasks(tasks)
        context.user_data.clear()
        icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢"}
        labels = {"Q1": "Срочно + Важно", "Q2": "Важно, не срочно", "Q3": "Срочно, не важно", "Q4": "Не срочно, не важно"}
        await q.edit_message_text(
            f"✅ *Задача добавлена!*\n\n📌 {task}\n{icons[p]} _{labels[p]}_{note}",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif d.startswith("view_"):
        qd = d.replace("view_", "")
        icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢", "done": "✅"}
        labels = {"Q1": "Срочно + Важно", "Q2": "Важно, не срочно", "Q3": "Делегировать", "Q4": "Потом", "done": "Выполненные"}
        items = tasks.get(qd, [])
        if not items:
            await q.edit_message_text(
                f"{icons[qd]} *{labels[qd]}*\n\n_Задач нет_ 🎉",
                reply_markup=back_btn(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        kb = []
        for i, t in enumerate(items):
            short = t[:38] + "..." if len(t) > 38 else t
            kb.append([InlineKeyboardButton(f"📌  {short}", callback_data=f"t_{qd}_{i}")])
        kb.append([InlineKeyboardButton("⬅️  Назад", callback_data="back_main")])
        await q.edit_message_text(
            f"{icons[qd]} *{labels[qd]}*\n_{len(items)} задач:_",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif d.startswith("t_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            kb = [
                [InlineKeyboardButton("✅  Выполнено", callback_data=f"done_{qd}_{i}")],
                [InlineKeyboardButton("🗑  Удалить", callback_data=f"del_{qd}_{i}")],
                [InlineKeyboardButton("⬅️  Назад", callback_data=f"view_{qd}")],
            ]
            await q.edit_message_text(
                f"📌 *{items[i]}*",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )

    elif d.startswith("done_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            tasks["done"].append(name)
            save_tasks(tasks)
            await q.edit_message_text(
                f"✅ *Выполнено!*\n\n_{name}_",
                reply_markup=main_menu(),
                parse_mode=ParseMode.MARKDOWN
            )

    elif d.startswith("del_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            save_tasks(tasks)
            await q.edit_message_text(
                f"🗑 *Удалено*\n\n_{name}_",
                reply_markup=main_menu(),
                parse_mode=ParseMode.MARKDOWN
            )

    elif d == "finances":
        earned = tasks.get("earnings", 0)
        goal = 4500
        bar, pct = progress_bar(earned, goal)
        debts = tasks.get("debts", {})
        total_debt_eur = debts.get("pacany", 0) + debts.get("shtrafy", 0)
        msg = f"""💰 *ФИНАНСЫ*

━━━━━━━━━━━━━━━
📈 *Прогресс к цели*
{bar} *{pct}%*
Заработано: *{earned}€*
Цель: *{goal}€*
Осталось: *{goal - earned}€*

━━━━━━━━━━━━━━━
💸 *Долги*
🔴 Пацаны: *{debts.get('pacany', 450)}€* _(срочно)_
🔴 Штрафы ПДД: *{debts.get('shtrafy', 1000)}€*
🟡 Общие долги: *{debts.get('obshie', 2500)}$*

Срочно нужно: *{total_debt_eur}€*"""
        kb = [
            [InlineKeyboardButton("➕  Добавить доход", callback_data="income")],
            [InlineKeyboardButton("💸  Отдал долг", callback_data="pay_debt")],
            [InlineKeyboardButton("⬅️  Назад", callback_data="back_main")],
        ]
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    elif d == "income":
        context.user_data["income"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await q.edit_message_text(
            "💰 *Добавить доход*\n\nСколько заработал? Напиши сумму в евро:\n\n_Например: 130_",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif d == "pay_debt":
        context.user_data["debt"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await q.edit_message_text(
            "💸 *Отдал долг*\n\nКому и сколько? Напиши:\n\n_Например: пацаны 200_",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    elif d == "ai_advice":
        await q.edit_message_text("🤖 _Анализирую твои задачи..._", parse_mode=ParseMode.MARKDOWN)
        now = datetime.now()
        advice = await ask_claude(
            f"Сейчас {get_day_ru()}, {now.strftime('%H:%M')}. Что мне делать прямо сейчас и сегодня? Дай конкретный план по часам. Учти мои задачи.",
            tasks
        )
        kb = [[InlineKeyboardButton("⬅️  Назад", callback_data="back_main")]]
        await q.edit_message_text(advice, reply_markup=InlineKeyboardMarkup(kb))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tasks = load_tasks()

    if context.user_data.get("add"):
        context.user_data["task"] = text
        context.user_data["add"] = False
        await update.message.reply_text(
            f"📌 *{text}*\n\nКакой приоритет?",
            reply_markup=priority_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif context.user_data.get("income"):
        context.user_data.clear()
        try:
            amount = float(''.join(c for c in text if c.isdigit() or c == '.'))
            tasks["earnings"] = tasks.get("earnings", 0) + amount
            save_tasks(tasks)
            bar, pct = progress_bar(tasks["earnings"], 4500)
            await update.message.reply_text(
                f"✅ *Доход записан!*\n\n➕ *+{amount}€*\n\n{bar} *{pct}%*\nИтого: *{tasks['earnings']}€* из 4500€",
                reply_markup=main_menu(),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text("Не понял сумму. Напиши просто число, например: 130", reply_markup=main_menu())

    elif context.user_data.get("debt"):
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ *Записал:* _{text}_",
            reply_markup=main_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

    else:
        response = await ask_claude(text, tasks)
        kb = [[InlineKeyboardButton("📋  Меню", callback_data="back_main")]]
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
