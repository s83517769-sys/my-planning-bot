import os
import json
import httpx
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
TASKS_FILE = "tasks.json"

SYSTEM_PROMPT = """Ты личный помощник, бизнес-стратег и маркетолог Саида. Думай как топовый бизнесмен — всегда фокус на том что даст деньги БЫСТРЕЕ.

ЛИЧНАЯ СИТУАЦИЯ:
- Живёт на Южном Кипре
- Цель: заработать 4500 евро за 30 дней
- Через 30 дней приедет девушка — семейный бюджет общий
- Футбол: понедельник и среда вечером (не планировать)
- Утро: 9:00 отжимания+душ+завтрак, 9:30-10:00 отчёты арбитраж

ФИНАНСОВЫЕ ЦЕЛИ:
- 1000 евро — штрафы ПДД (срочно, есть дедлайн)
- 400-500 евро — долг друзьям (отдать с первых заработков, не горит)
- 2500 долларов — общие долги (частями, ждут)
- 2000 евро — к приезду девушки

НАПРАВЛЕНИЯ БИЗНЕСА:
1. АРБИТРАЖ — Команды 00 и 52. Отчёты каждое утро. Помощник запускает до 20 аккаунтов в день.
2. ХИМЧИСТКА с Сашей (50/50) — уже работает, 3-4 заказа в неделю, реклама 300-500$ в месяц.
3. ХИМЧИСТКА через девочку — нестабильно, 1-2 заказа в неделю.
4. ХИМЧИСТКА НА ТРОИХ — самый быстрый старт, друзья готовы, нужен сайт и реклама.
5. ДЕВУШКА В КИЕВЕ — сайт + реклама, к приезду должны идти заказы.
6. САЙТ Google аккаунтов — полуготовый, продажа арбитражникам.

Отвечай на русском. Коротко и конкретно. Используй эмодзи."""

DAYS_RU = {
    "Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
    "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"
}

EXPENSE_CATS = {
    "food": "🛒 Еда",
    "transport": "🚗 Транспорт",
    "business": "💼 Бизнес",
    "personal": "👤 Личное",
    "other": "📦 Другое"
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
        "balance": 0,
        "debts": {"pacany": 450, "shtrafy": 0, "obshie": 0},
        "owe_me": [],
        "expenses": [],
        "income_log": []
    }

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def get_period_stats(tasks, days=1):
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    expenses = tasks.get("expenses", [])
    income_log = tasks.get("income_log", [])
    
    period_expenses = []
    period_income = []
    
    for e in expenses:
        try:
            dt = datetime.fromisoformat(e.get("date", ""))
            if dt >= cutoff:
                period_expenses.append(e)
        except:
            pass
    
    for i in income_log:
        try:
            dt = datetime.fromisoformat(i.get("date", ""))
            if dt >= cutoff:
                period_income.append(i)
        except:
            pass
    
    total_exp = sum(e.get("amount", 0) for e in period_expenses)
    total_inc = sum(i.get("amount", 0) for i in period_income)
    
    return total_exp, total_inc, period_expenses, period_income

def main_menu():
    tasks = load_tasks()
    q1 = len(tasks.get("Q1", []))
    q2 = len(tasks.get("Q2", []))
    q3 = len(tasks.get("Q3", []))
    q4 = len(tasks.get("Q4", []))
    balance = tasks.get("balance", 0)
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
        [InlineKeyboardButton(f"💰  Финансы · {balance}€", callback_data="finances")],
        [InlineKeyboardButton("🤖  Что делать сейчас?", callback_data="ai_advice")],
        [InlineKeyboardButton("❓  Приоритеты", callback_data="help_priority")],
    ]
    return InlineKeyboardMarkup(keyboard)

def finances_menu():
    keyboard = [
        [InlineKeyboardButton("➕  Доход", callback_data="income"),
         InlineKeyboardButton("➖  Расход", callback_data="expense")],
        [InlineKeyboardButton("👥  Мне должны", callback_data="owe_me_menu")],
        [InlineKeyboardButton("💸  Отдал долг", callback_data="pay_debt_menu")],
        [InlineKeyboardButton("📊  Статистика", callback_data="stats")],
        [InlineKeyboardButton("⬅️  Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def expense_cat_menu():
    keyboard = [
        [InlineKeyboardButton("🛒 Еда", callback_data="ecat_food"),
         InlineKeyboardButton("🚗 Транспорт", callback_data="ecat_transport")],
        [InlineKeyboardButton("💼 Бизнес", callback_data="ecat_business"),
         InlineKeyboardButton("👤 Личное", callback_data="ecat_personal")],
        [InlineKeyboardButton("📦 Другое", callback_data="ecat_other")],
        [InlineKeyboardButton("❌ Отмена", callback_data="finances")],
    ]
    return InlineKeyboardMarkup(keyboard)

def debt_menu():
    keyboard = [
        [InlineKeyboardButton("👥  Друзьям", callback_data="debt_pacany")],
        [InlineKeyboardButton("🚔  Штрафы ПДД", callback_data="debt_shtrafy")],
        [InlineKeyboardButton("💼  Общие долги", callback_data="debt_obshie")],
        [InlineKeyboardButton("❌  Отмена", callback_data="finances")],
    ]
    return InlineKeyboardMarkup(keyboard)

def priority_menu():
    keyboard = [
        [InlineKeyboardButton("🔴  Срочно + Важно (Q1)", callback_data="prio_Q1")],
        [InlineKeyboardButton("🔵  Важно, не срочно (Q2)", callback_data="prio_Q2")],
        [InlineKeyboardButton("🟡  Срочно, не важно (Q3)", callback_data="prio_Q3")],
        [InlineKeyboardButton("🟢  Не срочно, не важно (Q4)", callback_data="prio_Q4")],
        [InlineKeyboardButton("🤖  Пусть ИИ решит", callback_data="prio_AI")],
        [InlineKeyboardButton("❌  Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def ask_claude(message, tasks=None):
    now = datetime.now()
    context = f"\nСейчас: {get_day_ru()}, {now.strftime('%H:%M')}"
    if tasks:
        context += f"\nБаланс: {tasks.get('balance', 0)}€ · Заработано всего: {tasks.get('earnings', 0)}€"
        context += f"\nЗадачи Q1={tasks.get('Q1',[])} Q2={tasks.get('Q2',[])}"
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
                "max_tokens": 700,
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
    balance = tasks.get("balance", 0)
    bar, pct = progress_bar(earned, 4500)
    q1 = len(tasks.get("Q1", []))
    total_active = sum(len(tasks.get(q, [])) for q in ["Q1","Q2","Q3","Q4"])
    done = len(tasks.get("done", []))
    
    exp_day, inc_day, _, _ = get_period_stats(tasks, 1)

    text = (
        f"👋 Привет, Саид!\n\n"
        f"📅 {day} · {now.strftime('%H:%M')}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💳 Баланс: {balance}€\n"
        f"📈 Сегодня: +{inc_day}€ доход · -{exp_day}€ расход\n\n"
        f"💰 Прогресс к цели\n"
        f"{bar} {pct}%\n"
        f"{earned}€ из 4500€\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 Задачи\n"
        f"🔴 Срочных: {q1}  📌 Активных: {total_active}  ✅ Готово: {done}\n"
        f"━━━━━━━━━━━━━━━"
    )
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(welcome_text(), reply_markup=main_menu())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    tasks = load_tasks()

    if d == "back_main":
        await q.edit_message_text(welcome_text(), reply_markup=main_menu())

    elif d == "cancel":
        context.user_data.clear()
        await q.edit_message_text(welcome_text(), reply_markup=main_menu())

    elif d == "help_priority":
        text = (
            "❓ КАК РАССТАВЛЯТЬ ПРИОРИТЕТЫ\n\n"
            "🔴 Q1 — СРОЧНО + ВАЖНО\n"
            "Делать СЕЙЧАС. Если не сделаешь сегодня — потеряешь деньги.\n"
            "Примеры: реклама которая должна работать, штраф с дедлайном.\n\n"
            "🔵 Q2 — ВАЖНО, не срочно\n"
            "Делать каждый день блоком 2-3 часа. Отсюда приходит рост.\n"
            "Примеры: сайт химчистки, запуск рекламы, развитие бизнеса.\n\n"
            "🟡 Q3 — СРОЧНО, не важно\n"
            "Делегировать помощнику или делать быстро между делом.\n"
            "Примеры: отчёты, карты и ссылки для аккаунтов.\n\n"
            "🟢 Q4 — не срочно, не важно\n"
            "Удалить или отложить на месяц.\n\n"
            "💡 Правило: если не сделаю сегодня — потеряю деньги? Да = Q1. Нет = Q2."
        )
        kb = [[InlineKeyboardButton("⬅️  Назад", callback_data="back_main")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif d == "add_task":
        context.user_data["add"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
        await q.edit_message_text("✏️ Новая задача\n\nНапиши название:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("prio_"):
        p = d.replace("prio_", "")
        task = context.user_data.get("task", "")
        if not task:
            await q.edit_message_text(welcome_text(), reply_markup=main_menu())
            return
        if p == "AI":
            ai = await ask_claude(f"Определи приоритет Q1 Q2 Q3 или Q4 для задачи: {task}. Ответь только Q1, Q2, Q3 или Q4 и одно предложение почему.")
            p = "Q1" if "Q1" in ai else "Q2" if "Q2" in ai else "Q3" if "Q3" in ai else "Q4"
            note = f"\n\n🤖 {ai}"
        else:
            note = ""
        tasks[p].append(task)
        save_tasks(tasks)
        context.user_data.clear()
        icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢"}
        labels = {"Q1": "Срочно + Важно", "Q2": "Важно, не срочно", "Q3": "Делегировать", "Q4": "Потом"}
        await q.edit_message_text(
            f"✅ Добавлено!\n\n📌 {task}\n{icons[p]} {labels[p]}{note}",
            reply_markup=main_menu()
        )

    elif d.startswith("view_"):
        qd = d.replace("view_", "")
        icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢", "done": "✅"}
        labels = {"Q1": "Срочно + Важно", "Q2": "Важно, не срочно", "Q3": "Делегировать", "Q4": "Потом", "done": "Выполненные"}
        items = tasks.get(qd, [])
        if not items:
            kb = [[InlineKeyboardButton("⬅️  Назад", callback_data="back_main")]]
            await q.edit_message_text(f"{icons[qd]} {labels[qd]}\n\nЗадач нет 🎉", reply_markup=InlineKeyboardMarkup(kb))
            return
        kb = []
        for i, t in enumerate(items):
            short = t[:38] + "..." if len(t) > 38 else t
            kb.append([InlineKeyboardButton(f"📌  {short}", callback_data=f"t_{qd}_{i}")])
        kb.append([InlineKeyboardButton("⬅️  Назад", callback_data="back_main")])
        await q.edit_message_text(f"{icons[qd]} {labels[qd]}\n{len(items)} задач:", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("t_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            kb = [
                [InlineKeyboardButton("✅  Выполнено", callback_data=f"done_{qd}_{i}")],
                [InlineKeyboardButton("🔄  Перенести", callback_data=f"move_{qd}_{i}")],
                [InlineKeyboardButton("🗑  Удалить", callback_data=f"del_{qd}_{i}")],
                [InlineKeyboardButton("⬅️  Назад", callback_data=f"view_{qd}")],
            ]
            await q.edit_message_text(f"📌 {items[i]}", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("move_") and not d.startswith("move_to_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢"}
            labels = {"Q1": "Срочно", "Q2": "Важно", "Q3": "Делегировать", "Q4": "Потом"}
            kb = []
            for target in ["Q1", "Q2", "Q3", "Q4"]:
                if target != qd:
                    kb.append([InlineKeyboardButton(f"{icons[target]}  {labels[target]}", callback_data=f"move_to_{target}_{qd}_{i}")])
            kb.append([InlineKeyboardButton("⬅️  Назад", callback_data=f"t_{qd}_{i}")])
            await q.edit_message_text(
                f"🔄 Перенести:\n📌 {items[i]}\n\nВыбери новый приоритет:",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    elif d.startswith("move_to_"):
        rest = d.replace("move_to_", "")
        parts = rest.split("_", 2)
        p, old_q, i = parts[0], parts[1], int(parts[2])
        old_items = tasks.get(old_q, [])
        if i < len(old_items):
            task_name = old_items.pop(i)
            tasks[p].append(task_name)
            save_tasks(tasks)
            icons = {"Q1": "🔴", "Q2": "🔵", "Q3": "🟡", "Q4": "🟢"}
            labels = {"Q1": "Срочно", "Q2": "Важно", "Q3": "Делегировать", "Q4": "Потом"}
            await q.edit_message_text(
                f"🔄 Перенесено!\n\n📌 {task_name}\n{icons[p]} {labels[p]}",
                reply_markup=main_menu()
            )

    elif d.startswith("done_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            tasks["done"].append(name)
            save_tasks(tasks)
            await q.edit_message_text(f"✅ Выполнено!\n\n{name}", reply_markup=main_menu())

    elif d.startswith("del_"):
        parts = d.split("_", 2)
        qd, i = parts[1], int(parts[2])
        items = tasks.get(qd, [])
        if i < len(items):
            name = items.pop(i)
            save_tasks(tasks)
            await q.edit_message_text(f"🗑 Удалено\n\n{name}", reply_markup=main_menu())

    elif d == "finances":
        context.user_data.clear()
        earned = tasks.get("earnings", 0)
        balance = tasks.get("balance", 0)
        debts = tasks.get("debts", {})
        owe_me = tasks.get("owe_me", [])
        bar, pct = progress_bar(earned, 4500)
        
        exp_day, inc_day, _, _ = get_period_stats(tasks, 1)
        exp_week, inc_week, _, _ = get_period_stats(tasks, 7)
        exp_month, inc_month, _, _ = get_period_stats(tasks, 30)
        
        owe_total = sum(o.get("amount", 0) for o in owe_me)
        
        msg = (
            f"💰 ФИНАНСЫ\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💳 Текущий баланс: {balance}€\n"
            f"📈 К цели: {bar} {pct}%\n"
            f"{earned}€ из 4500€\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Статистика расходов:\n"
            f"Сегодня: -{exp_day}€ · +{inc_day}€\n"
            f"Неделя: -{exp_week}€ · +{inc_week}€\n"
            f"Месяц: -{exp_month}€ · +{inc_month}€\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💸 Мои долги:\n"
            f"🔴 Штрафы ПДД: {debts.get('shtrafy', 1000)}€\n"
            f"🔵 Друзьям: {debts.get('pacany', 450)}€\n"
            f"🟡 Общие: {debts.get('obshie', 2500)}$\n\n"
            f"📥 Мне должны: {owe_total}€ ({len(owe_me)} чел.)"
        )
        await q.edit_message_text(msg, reply_markup=finances_menu())

    elif d == "income":
        context.user_data["income"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="finances")]]
        await q.edit_message_text(
            "💰 Добавить доход\n\nНапиши: сумма описание\n\nПримеры:\n130 химчистка авто\n200 клининг с Сашей\n50 левак арбитраж",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d == "expense":
        context.user_data["expense_wait"] = True
        await q.edit_message_text(
            "➖ Добавить расход\n\nВыбери категорию:",
            reply_markup=expense_cat_menu()
        )

    elif d.startswith("ecat_"):
        cat = d.replace("ecat_", "")
        context.user_data["expense_cat"] = cat
        context.user_data["expense_wait"] = False
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="finances")]]
        await q.edit_message_text(
            f"➖ Расход · {EXPENSE_CATS[cat]}\n\nНапиши: сумма описание\n\nПримеры:\n15 обед\n50 бензин\n30 химия для химчистки",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d == "owe_me_menu":
        owe_me = tasks.get("owe_me", [])
        if not owe_me:
            kb = [
                [InlineKeyboardButton("➕ Добавить", callback_data="add_owe")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="finances")],
            ]
            await q.edit_message_text("📥 Мне должны\n\nПока никто не должен.", reply_markup=InlineKeyboardMarkup(kb))
            return
        text = "📥 МНЕ ДОЛЖНЫ:\n\n"
        total = 0
        for o in owe_me:
            text += f"👤 {o.get('name')} — {o.get('amount')}€\n"
            if o.get('desc'):
                text += f"   за: {o.get('desc')}\n"
            total += o.get('amount', 0)
        text += f"\n💰 Итого: {total}€"
        kb = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_owe")],
            [InlineKeyboardButton("✅ Вернули долг", callback_data="owe_paid")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="finances")],
        ]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif d == "add_owe":
        context.user_data["add_owe"] = True
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="owe_me_menu")]]
        await q.edit_message_text(
            "📥 Кто тебе должен?\n\nНапиши: имя сумма описание\n\nПримеры:\nСаша 200 за химчистку\nАндрей 150 за работу",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d == "owe_paid":
        owe_me = tasks.get("owe_me", [])
        if not owe_me:
            await q.edit_message_text("Нет должников.", reply_markup=finances_menu())
            return
        kb = []
        for i, o in enumerate(owe_me):
            kb.append([InlineKeyboardButton(f"✅ {o.get('name')} — {o.get('amount')}€", callback_data=f"owe_done_{i}")])
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="owe_me_menu")])
        await q.edit_message_text("Кто вернул долг?", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("owe_done_"):
        i = int(d.replace("owe_done_", ""))
        owe_me = tasks.get("owe_me", [])
        if i < len(owe_me):
            person = owe_me.pop(i)
            tasks["balance"] = tasks.get("balance", 0) + person.get("amount", 0)
            tasks["earnings"] = tasks.get("earnings", 0) + person.get("amount", 0)
            tasks["income_log"] = tasks.get("income_log", [])
            tasks["income_log"].append({
                "amount": person.get("amount", 0),
                "desc": f"Вернул долг: {person.get('name')}",
                "date": datetime.now().isoformat()
            })
            save_tasks(tasks)
            await q.edit_message_text(
                f"✅ {person.get('name')} вернул {person.get('amount')}€!\n\nБаланс: {tasks['balance']}€",
                reply_markup=finances_menu()
            )

    elif d == "pay_debt_menu":
        await q.edit_message_text("💸 Кому отдал долг?", reply_markup=debt_menu())

    elif d.startswith("debt_"):
        debt_key = d.replace("debt_", "")
        context.user_data["pay_debt"] = debt_key
        names = {"pacany": "друзьям", "shtrafy": "штрафы ПДД", "obshie": "общие долги"}
        current = tasks.get("debts", {}).get(debt_key, 0)
        currency = "$" if debt_key == "obshie" else "€"
        kb = [[InlineKeyboardButton("❌ Отмена", callback_data="finances")]]
        await q.edit_message_text(
            f"💸 Долг: {names[debt_key]}\nОстаток: {current}{currency}\n\nСколько отдал?",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif d == "stats":
        exp_day, inc_day, exp_list, _ = get_period_stats(tasks, 1)
        exp_week, inc_week, _, _ = get_period_stats(tasks, 7)
        exp_month, inc_month, _, _ = get_period_stats(tasks, 30)
        
        text = (
            f"📊 СТАТИСТИКА\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 Сегодня\n"
            f"Доход: +{inc_day}€ · Расход: -{exp_day}€\n"
            f"Итог: {inc_day - exp_day}€\n\n"
            f"📅 Неделя\n"
            f"Доход: +{inc_week}€ · Расход: -{exp_week}€\n"
            f"Итог: {inc_week - exp_week}€\n\n"
            f"📅 Месяц\n"
            f"Доход: +{inc_month}€ · Расход: -{exp_month}€\n"
            f"Итог: {inc_month - exp_month}€\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💳 Баланс: {tasks.get('balance', 0)}€"
        )
        kb = [[InlineKeyboardButton("⬅️  Назад", callback_data="finances")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif d == "ai_advice":
        await q.edit_message_text("🤖 Анализирую твою ситуацию...")
        now = datetime.now()
        advice = await ask_claude(
            f"Сейчас {get_day_ru()}, {now.strftime('%H:%M')}. Что делать прямо сейчас чтобы максимально быстро заработать? Конкретный план по часам.",
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
        await update.message.reply_text(f"📌 {text}\n\nКакой приоритет?", reply_markup=priority_menu())

    elif context.user_data.get("income"):
        context.user_data.clear()
        try:
            parts = text.split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else "доход"
            tasks["earnings"] = tasks.get("earnings", 0) + amount
            tasks["balance"] = tasks.get("balance", 0) + amount
            tasks.setdefault("income_log", []).append({
                "amount": amount, "desc": desc,
                "date": datetime.now().isoformat()
            })
            save_tasks(tasks)
            bar, pct = progress_bar(tasks["earnings"], 4500)
            await update.message.reply_text(
                f"✅ Доход записан!\n\n+{amount}€ · {desc}\n\n{bar} {pct}%\nБаланс: {tasks['balance']}€\nК цели: {tasks['earnings']}€ из 4500€",
                reply_markup=main_menu()
            )
        except:
            await update.message.reply_text("Напиши: сумма описание\nНапример: 130 химчистка авто", reply_markup=main_menu())

    elif context.user_data.get("expense_cat"):
        cat = context.user_data["expense_cat"]
        context.user_data.clear()
        try:
            parts = text.split(maxsplit=1)
            amount = float(parts[0])
            desc = parts[1] if len(parts) > 1 else "расход"
            tasks["balance"] = tasks.get("balance", 0) - amount
            tasks.setdefault("expenses", []).append({
                "amount": amount, "desc": desc, "cat": cat,
                "date": datetime.now().isoformat()
            })
            save_tasks(tasks)
            await update.message.reply_text(
                f"➖ Расход записан!\n\n-{amount}€ · {desc}\n{EXPENSE_CATS[cat]}\n\nБаланс: {tasks['balance']}€",
                reply_markup=main_menu()
            )
        except:
            await update.message.reply_text("Напиши: сумма описание\nНапример: 15 обед", reply_markup=main_menu())

    elif context.user_data.get("add_owe"):
        context.user_data.clear()
        try:
            parts = text.split(maxsplit=2)
            name = parts[0]
            amount = float(parts[1])
            desc = parts[2] if len(parts) > 2 else ""
            tasks.setdefault("owe_me", []).append({"name": name, "amount": amount, "desc": desc})
            save_tasks(tasks)
            await update.message.reply_text(
                f"📥 Записал!\n\n👤 {name} должен {amount}€\n{desc}",
                reply_markup=main_menu()
            )
        except:
            await update.message.reply_text("Напиши: имя сумма описание\nНапример: Саша 200 за химчистку", reply_markup=main_menu())

    elif context.user_data.get("pay_debt"):
        debt_key = context.user_data["pay_debt"]
        context.user_data.clear()
        try:
            amount = float(''.join(c for c in text if c.isdigit() or c == '.'))
            current = tasks.get("debts", {}).get(debt_key, 0)
            new_amount = max(0, current - amount)
            tasks["debts"][debt_key] = new_amount
            tasks["balance"] = tasks.get("balance", 0) - amount
            save_tasks(tasks)
            names = {"pacany": "Друзьям", "shtrafy": "Штрафы ПДД", "obshie": "Общие долги"}
            currency = "$" if debt_key == "obshie" else "€"
            await update.message.reply_text(
                f"✅ Отдал долг!\n\n💸 {names[debt_key]}\nОтдал: {amount}{currency}\nОсталось: {new_amount}{currency}\n\nБаланс: {tasks['balance']}€",
                reply_markup=main_menu()
            )
        except:
            await update.message.reply_text("Напиши просто число, например: 200", reply_markup=main_menu())

    else:
        response = await ask_claude(text, tasks)
        kb = [[InlineKeyboardButton("📋  Меню", callback_data="back_main")]]
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot v5 started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
