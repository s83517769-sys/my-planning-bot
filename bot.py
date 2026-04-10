import os
import json
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

TASKS_FILE = "tasks.json"

SYSTEM_PROMPT = """Ты личный помощник и бизнес-планировщик Саида. Живёт на Южном Кипре.
Цель: заработать 4500 евро за 30 дней.
Долги: пацанам 400-500 евро СРОЧНО, штрафы ПДД 1000 евро, общие долги 2500 долларов.
К приезду девушки через 30 дней нужно 2000 евро + квартира + авто.

Направления:
1. Реклама девушке клининг Киев Google Ads - СРОЧНО
2. Реклама дяде Саше клининг FB + креативы - СРОЧНО  
3. Химчистка авто 100-130 евро, мебель от 50 евро - брать максимум заказов
4. Сайт химчистки на троих пацанов
5. Сайт Google аккаунтов - доделать тексты + реклама
6. 20 аккаунтов в день арбитраж + карты + ссылки
7. Отчёты арбитраж каждое утро 9:30
8. Сайт для девушки - дедлайн 30 дней
9. Клуб предпринимателей Кипр

Расписание: 9:00 отжимания+душ+завтрак, 9:30-10:00 отчёты арбитраж, футбол пн и ср вечером.
Питание: правильное, цель похудение, бюджет 250 евро/месяц.

Отвечай на русском. Коротко и конкретно как опытный бизнесмен. 
Когда спрашивают про приоритеты - думай что даст деньги СЕГОДНЯ."""

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"Q1": [], "Q2": [], "Q3": [], "Q4": [], "done": [], "earnings": 0, "debts": {"pacany": 450, "shtrafy": 1000, "obshie": 2500}}

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить задачу", callback_data="add_task")],
        [
            InlineKeyboardButton("🔴 Срочные", callback_data="view_Q1"),
            InlineKeyboardButton("🔵 Важные", callback_data="view_Q2"),
        ],
        [
            InlineKeyboardButton("🟡 Делегировать", callback_data="view_Q3"),
            InlineKeyboardButton("🟢 Потом", callback_data="view_Q4"),
        ],
        [InlineKeyboardButton("✅ Выполненные", callback_data="view_done")],
        [InlineKeyboardButton("💰 Финансы", callback_data="finances")],
        [InlineKeyboardButton("🤖 Что делать сейчас?", callback_data="ai_advice")],
    ]
    return InlineKeyboardMarkup(keyboard)

def priority_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔴 Срочно + Важно (Q1)", callback_data="prio_Q1")],
        [InlineKeyboardButton("🔵 Важно, не срочно (Q2)", callback_data="prio_Q2")],
        [InlineKeyboardButton("🟡 Срочно, не важно (Q3)", callback_data="prio_Q3")],
        [InlineKeyboardButton("🟢 Не срочно, не важно (Q4)", callback_data="prio_Q4")],
        [InlineKeyboardButton("🤖 Пусть ИИ решит", callback_data="prio_AI")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

def task_action_keyboard(task_id, quadrant):
    keyboard = [
        [InlineKeyboardButton("✅ Выполнено", callback_data=f"done_{quadrant}_{task_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{quadrant}_{task_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def ask_claude(user_message: str, context_tasks: dict = None) -> str:
    import httpx
    
    tasks_context = ""
    if context_tasks:
        tasks_context = f"\n\nТекущие задачи пользователя:\nСрочные (Q1): {context_tasks.get('Q1', [])}\nВажные (Q2): {context_tasks.get('Q2', [])}\nДелегировать (Q3): {context_tasks.get('Q3', [])}\nПотом (Q4): {context_tasks.get('Q4', [])}\nЗаработано: {context_tasks.get('earnings', 0)} евро"
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "system": SYSTEM_PROMPT + tasks_context,
                "messages": [{"role": "user", "content": user_message}],
            }
        )
        data = response.json()
        return data["content"][0]["text"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет, Саид!\n\nЯ твой личный планировщик. Выбери действие:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tasks = load_tasks()

    if data == "back_main":
        await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())

    elif data == "add_task":
        context.user_data["waiting_for_task"] = True
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await query.edit_message_text(
            "✏️ Напиши название задачи:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())

    elif data.startswith("prio_"):
        priority = data.replace("prio_", "")
        task_name = context.user_data.get("pending_task", "")
        
        if not task_name:
            await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())
            return

        if priority == "AI":
            ai_response = await ask_claude(f"Определи приоритет по матрице Эйзенхауэра для задачи: '{task_name}'. Ответь только: Q1, Q2, Q3 или Q4 и одно предложение почему.", tasks)
            if "Q1" in ai_response:
                priority = "Q1"
            elif "Q2" in ai_response:
                priority = "Q2"
            elif "Q3" in ai_response:
                priority = "Q3"
            else:
                priority = "Q4"
            ai_comment = ai_response
        else:
            ai_comment = None

        tasks[priority].append(task_name)
        save_tasks(tasks)
        context.user_data.clear()

        labels = {"Q1": "🔴 Срочно", "Q2": "🔵 Важно", "Q3": "🟡 Делегировать", "Q4": "🟢 Потом"}
        msg = f"✅ Задача добавлена!\n\n📌 {task_name}\n{labels[priority]}"
        if ai_comment:
            msg += f"\n\n🤖 ИИ: {ai_comment}"
        
        await query.edit_message_text(msg, reply_markup=main_menu_keyboard())

    elif data.startswith("view_"):
        quadrant = data.replace("view_", "")
        labels = {
            "Q1": "🔴 Срочно + Важно",
            "Q2": "🔵 Важно, не срочно", 
            "Q3": "🟡 Срочно, не важно",
            "Q4": "🟢 Не срочно, не важно",
            "done": "✅ Выполненные"
        }
        
        task_list = tasks.get(quadrant, [])
        
        if not task_list:
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]]
            await query.edit_message_text(
                f"{labels[quadrant]}\n\nЗадач нет 🎉",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = []
        for i, task in enumerate(task_list):
            short = task[:30] + "..." if len(task) > 30 else task
            keyboard.append([InlineKeyboardButton(f"📌 {short}", callback_data=f"task_{quadrant}_{i}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
        
        await query.edit_message_text(
            f"{labels[quadrant]} — {len(task_list)} задач:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("task_"):
        parts = data.split("_", 2)
        quadrant = parts[1]
        task_id = int(parts[2])
        task_list = tasks.get(quadrant, [])
        
        if task_id < len(task_list):
            task_name = task_list[task_id]
            await query.edit_message_text(
                f"📌 {task_name}",
                reply_markup=task_action_keyboard(task_id, quadrant)
            )

    elif data.startswith("done_"):
        parts = data.split("_", 2)
        quadrant = parts[1]
        task_id = int(parts[2])
        task_list = tasks.get(quadrant, [])
        
        if task_id < len(task_list):
            task_name = task_list.pop(task_id)
            tasks["done"].append(task_name)
            save_tasks(tasks)
            await query.edit_message_text(f"✅ Выполнено: {task_name}", reply_markup=main_menu_keyboard())

    elif data.startswith("del_"):
        parts = data.split("_", 2)
        quadrant = parts[1]
        task_id = int(parts[2])
        task_list = tasks.get(quadrant, [])
        
        if task_id < len(task_list):
            task_name = task_list.pop(task_id)
            save_tasks(tasks)
            await query.edit_message_text(f"🗑 Удалено: {task_name}", reply_markup=main_menu_keyboard())

    elif data == "finances":
        earnings = tasks.get("earnings", 0)
        goal = 4500
        progress = int((earnings / goal) * 100)
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        
        debts = tasks.get("debts", {})
        
        msg = f"""💰 ФИНАНСЫ

📈 Прогресс к цели:
{bar} {progress}%
Заработано: {earnings}€ / {goal}€

💸 Долги:
🔴 Пацаны: {debts.get('pacany', 450)}€
🔴 Штрафы ПДД: {debts.get('shtrafy', 1000)}€  
🟡 Общие долги: {debts.get('obshie', 2500)}$

Осталось до цели: {goal - earnings}€"""

        keyboard = [
            [InlineKeyboardButton("➕ Добавить доход", callback_data="add_income")],
            [InlineKeyboardButton("➖ Отдал долг", callback_data="pay_debt")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_income":
        context.user_data["waiting_for_income"] = True
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await query.edit_message_text("💰 Сколько заработал? Напиши сумму в евро:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "pay_debt":
        context.user_data["waiting_for_debt"] = True
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await query.edit_message_text("💸 Кому и сколько отдал? Например: пацаны 200", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "ai_advice":
        await query.edit_message_text("🤖 Думаю...")
        today = datetime.now().strftime("%A")
        advice = await ask_claude(f"Сегодня {today}. Что мне делать прямо сейчас? Дай конкретный план на сегодня по часам. Учти мои текущие задачи.", tasks)
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]]
        await query.edit_message_text(f"🤖 План на сегодня:\n\n{advice}", reply_markup=InlineKeyboardMarkup(keyboard))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tasks = load_tasks()

    if context.user_data.get("waiting_for_task"):
        context.user_data["pending_task"] = text
        context.user_data["waiting_for_task"] = False
        await update.message.reply_text(
            f"📌 Задача: {text}\n\nКакой приоритет?",
            reply_markup=priority_keyboard()
        )

    elif context.user_data.get("waiting_for_income"):
        context.user_data.clear()
        try:
            amount = float(''.join(filter(lambda x: x.isdigit() or x == '.', text)))
            tasks["earnings"] = tasks.get("earnings", 0) + amount
            save_tasks(tasks)
            goal = 4500
            earned = tasks["earnings"]
            progress = int((earned / goal) * 100)
            await update.message.reply_text(
                f"✅ Добавлено: +{amount}€\n\n💰 Всего заработано: {earned}€\n📈 Прогресс: {progress}% от цели {goal}€",
                reply_markup=main_menu_keyboard()
            )
        except:
            await update.message.reply_text("Не понял сумму. Попробуй ещё раз.", reply_markup=main_menu_keyboard())

    elif context.user_data.get("waiting_for_debt"):
        context.user_data.clear()
        await update.message.reply_text(f"✅ Записал: {text}", reply_markup=main_menu_keyboard())

    else:
        response = await ask_claude(text, tasks)
        keyboard = [[InlineKeyboardButton("📋 Главное меню", callback_data="back_main")]]
        await update.message.reply_text(f"🤖 {response}", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    q1_count = len(tasks.get("Q1", []))
    earned = tasks.get("earnings", 0)
    
    msg = f"""🌅 Доброе утро, Саид!

⏰ 9:00 — отжимания, душ, завтрак
📊 9:30 — отчёты арбитраж

🔴 Срочных задач: {q1_count}
💰 Заработано: {earned}€ / 4500€

Что делаем сегодня?"""
    
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=msg,
        reply_markup=main_menu_keyboard()
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Morning reminder at 9:00
    if OWNER_ID:
        app.job_queue.run_daily(
            send_morning_reminder,
            time=time(9, 0),
        )
    
    print("Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
