import json
import asyncio
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, PollAnswerHandler

TOKEN = "7963132152:AAFxdth1fecPewJrDDZl8F1n2cJWsfaOE2w"
CHANNEL_ID = "@iisersmartprep"

def init_db():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_progress
                 (user_id INTEGER PRIMARY KEY, target_day TEXT, question_index INTEGER, score INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS active_polls
                 (poll_id TEXT PRIMARY KEY, user_id INTEGER, correct_option_id INTEGER)''')
    # Use the users table created by database.py
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 username TEXT,
                 score INTEGER DEFAULT 0,
                 correct INTEGER DEFAULT 0,
                 wrong INTEGER DEFAULT 0,
                 streak INTEGER DEFAULT 0,
                 last_played TEXT)''')
    conn.commit()
    conn.close()

def get_target_day():
    start_date = datetime(2026, 3, 10)
    today = datetime.now()
    day_number = (today - start_date).days + 1
    if day_number < 1:
        day_number = 1
    return f"day{day_number}"

def load_quiz_data():
    try:
        with open("quiz_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading quiz_data.json: {e}")
        return {}

async def post_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to post the daily message to the channel."""
    target_day = get_target_day()
    bot_link = f"https://t.me/{context.bot.username}"
    keyboard = [[InlineKeyboardButton("▶ Start Quiz", url=bot_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (f"🎯 {target_day.capitalize()} Mock Test\n\n"
           "20 Questions\n"
           "Subjects:\nPhysics • Chemistry • Mathematics • Biology\n\n"
           "Click below to start the quiz.")
    
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, reply_markup=reply_markup)
        if update.message:
            await update.message.reply_text("Posted daily message to channel.")
        else:
            print("Posted daily message to channel.")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"Error: {e}")
        print(f"Error posting daily message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_day = get_target_day()
    
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    
    # Track username if available
    username = update.effective_user.username or update.effective_user.first_name
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    
    # Initialize user state for the new quiz
    c.execute("INSERT OR REPLACE INTO user_progress (user_id, target_day, question_index, score) VALUES (?, ?, 0, 0)", 
              (user_id, target_day))
    
    # Clear any old active polls for this user to be safe
    c.execute("DELETE FROM active_polls WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    day_num = get_target_day().replace('day', 'Day')
    intro_message = (
        f"🎯 IISER SMART PREP — {day_num} Mock Test\n\n"
        "Subjects:\n"
        "Physics • Chemistry • Mathematics • Biology\n\n"
        f"Questions: 20\n"
        "Marking Scheme:\n"
        "✔ Correct: +4\n"
        "❌ Wrong: −1\n\n"
        "Recommended Time: 20 minutes\n\n"
        "All the best! 🚀"
    )
    await update.message.reply_text(intro_message)
    
    # Add a short delay then send the first question
    await asyncio.sleep(1)
    await send_next_question(user_id, context)

async def send_next_question(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = load_quiz_data()
    
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT target_day, question_index, score FROM user_progress WHERE user_id=?", (user_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return
        
    target_day, q_index, score = row
    
    if target_day not in data:
        await context.bot.send_message(chat_id=user_id, text=f"Quiz for {target_day} is not available yet.")
        conn.close()
        return

    quiz = data[target_day]
    subjects = ["physics", "chemistry", "mathematics", "biology"]
    
    # Flatten the questions
    flat_questions = []
    for subj in subjects:
        if subj in quiz:
            for q in quiz[subj]:
                flat_questions.append((subj, q))
                
    total_questions = len(flat_questions)
    
    if q_index < total_questions:
        subject, q = flat_questions[q_index]
        count = q_index + 1
        
        raw_question = q.get("question", "No question")
        question_text = f"Question {count}/{total_questions}\nSubject: {subject.capitalize()}\n\n{raw_question}"
        
        if len(question_text) > 300:
            question_text = question_text[:297] + "..."
            
        options = q.get("options", ["A", "B", "C", "D"])
        options = [opt[:97] + "..." if len(opt) > 100 else opt for opt in options]
        
        explanation = q.get("explanation", "")
        if len(explanation) > 200:
            explanation = explanation[:197] + "..."
            
        try:
            msg = await context.bot.send_poll(
                chat_id=user_id,
                question=question_text,
                options=options,
                type="quiz",
                correct_option_id=q.get("correct", 0),
                explanation=explanation,
                is_anonymous=False, # Required to receive PollAnswer events
                read_timeout=30,
                connect_timeout=30
            )
            
            # Save poll_id to active_polls to track the answer
            c.execute("INSERT OR REPLACE INTO active_polls (poll_id, user_id, correct_option_id) VALUES (?, ?, ?)", 
                      (msg.poll.id, user_id, q.get("correct", 0)))
            conn.commit()
            print(f"Sent question {count} to user {user_id}")
            
        except Exception as e:
            print(f"Error sending question to {user_id}: {e}")
            await context.bot.send_message(chat_id=user_id, text="Sorry, an error occurred while sending the question. Please try /start again.")
    else:
        # Quiz finished! Ensure we don't send this multiple times by removing progress immediately
        c.execute("DELETE FROM user_progress WHERE user_id=?", (user_id,))
        
        c.execute("SELECT streak, correct, wrong, score, last_played FROM users WHERE user_id=?", (user_id,))
        stat_row = c.fetchone()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        wrong_this_round = total_questions - score
        
        if stat_row:
            streak, total_correct, total_wrong, total_score, last_played = stat_row
            
            # Note: total_score tracking logic may be specific to how you want to weight things.
            # E.g. +4 for correct, -1 for wrong. Since you have total correct separately, let's keep score mapping to +4/-1 logic.
            round_score = (score * 4) - wrong_this_round
            
            if last_played != today_str:
                streak += 1
                total_correct += score
                total_wrong += wrong_this_round
                total_score += round_score
                
                c.execute("UPDATE users SET streak=?, correct=?, wrong=?, score=?, last_played=? WHERE user_id=?", 
                          (streak, total_correct, total_wrong, total_score, today_str, user_id))
        else:
            streak = 1
            total_correct = score
            total_wrong = wrong_this_round
            round_score = (score * 4) - wrong_this_round
            total_score = round_score
            c.execute("UPDATE users SET streak=?, correct=?, wrong=?, score=?, last_played=? WHERE user_id=?", 
                      (streak, total_correct, total_wrong, total_score, today_str, user_id))
            
        conn.commit()
        
        round_score = (score * 4) - wrong_this_round
        
        end_message = (
            "✅ <b>Test Completed!</b>\n\n"
            "Calculate your score:\n\n"
            "Correct Answer = +4\n"
            "Wrong Answer = −1\n\n"
            f"<b>Your Result: {score} correct, {wrong_this_round} wrong</b>\n"
            f"<b>Your Score: {round_score} / 80</b>\n\n"
            "Maximum Marks = 80\n\n"
            "Share your score in the comments! 👇\n\n"
            "<i>⏰ Next Mock Test: Tomorrow 8:00 AM</i>"
        )
        promo_message = (
            "📊 <b>Want full mock tests?</b>\n\n"
            "Visit: https://iisersmartprep.space"
        )
        streak_message = f"🔥 Current Streak: {streak} days\n🏆 Lifetime Correct Answers: {total_correct}"
        
        await context.bot.send_message(chat_id=user_id, text=end_message, parse_mode="HTML")
        await asyncio.sleep(1)
        await context.bot.send_message(chat_id=user_id, text=streak_message)
        await asyncio.sleep(1)
        await context.bot.send_message(chat_id=user_id, text=promo_message, parse_mode="HTML")
        print(f"User {user_id} completed quiz {target_day} with score {score}")
        
    conn.close()

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user_id = answer.user.id
    selected_options = answer.option_ids
    
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT user_id, correct_option_id FROM active_polls WHERE poll_id=?", (poll_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return
        
    poll_user_id, correct_option_id = row
    
    # Check if correct user
    if user_id != poll_user_id:
        conn.close()
        return
        
    # Check if correct answer
    is_correct = len(selected_options) > 0 and selected_options[0] == correct_option_id
    
    c.execute("SELECT question_index, score FROM user_progress WHERE user_id=?", (user_id,))
    prog_row = c.fetchone()
    if prog_row:
        q_index, score = prog_row
        if is_correct:
            score += 1
        q_index += 1
        c.execute("UPDATE user_progress SET question_index=?, score=? WHERE user_id=?", (q_index, score, user_id))
    
    # Remove poll from active_polls
    c.execute("DELETE FROM active_polls WHERE poll_id=?", (poll_id,))
    conn.commit()
    conn.close()
    
    # We want to wait a little bit so the user can read the explanation before they get the next poll
    await asyncio.sleep(3)
    
    # Send next question asynchronously
    asyncio.create_task(send_next_question(user_id, context))

if __name__ == "__main__":
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("post", post_daily))
    application.add_handler(PollAnswerHandler(receive_poll_answer))
    
    print("Bot is running in interactive mode. Press Ctrl+C to stop.")
    application.run_polling()