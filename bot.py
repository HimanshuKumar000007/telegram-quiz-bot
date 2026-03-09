import json
import asyncio
import sys
from telegram import Bot

TOKEN = "7963132152:AAFxdth1fecPewJrDDZl8F1n2cJWsfaOE2w"
CHANNEL_ID = "@iisersmartprep"

async def main(target_day):
    # Setup bot
    bot = Bot(token=TOKEN)

    # Load quiz data
    try:
        with open("quiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading quiz_data.json: {e}")
        return

    if target_day not in data:
        print(f"Error: '{target_day}' not found in quiz_data.json")
        print(f"Available days: {', '.join(data.keys())}")
        return

    quiz = data[target_day]
    subjects = ["physics", "chemistry", "mathematics", "biology"]

    # Send introductory message
    intro_message = (
        f"🎯 <b>Welcome to {target_day.capitalize()} Mock Test!</b> 🎯\n\n"
        "<i>Get ready to test your knowledge with today's questions from Physics, Chemistry, Mathematics, and Biology.</i>\n\n"
        "Best of luck! 🚀\n"
        "------------------------------------------------"
    )
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID, 
            text=intro_message, 
            parse_mode="HTML",
            read_timeout=30,
            connect_timeout=30
        )
        await asyncio.sleep(2)
        print("Sent introductory message.")
    except Exception as e:
        print(f"Error sending intro message: {e}")

    count = 1
    total_questions = sum(len(quiz[s]) for s in subjects if s in quiz)

    for subject in subjects:
        if subject in quiz:
            for q in quiz[subject]:
                try:
                    raw_question = q.get("question", "No question")
                    question_text = f"Question {count}/{total_questions}\nSubject: {subject.capitalize()}\n\n{raw_question}"
                    
                    if len(question_text) > 300:
                        question_text = question_text[:297] + "..."
                        
                    options = q.get("options", ["A", "B", "C", "D"])
                    options = [opt[:97] + "..." if len(opt) > 100 else opt for opt in options]
                    
                    explanation = q.get("explanation", "")
                    if len(explanation) > 200:
                        explanation = explanation[:197] + "..."
                        
                    await bot.send_poll(
                        chat_id=CHANNEL_ID,
                        question=question_text,
                        options=options,
                        type="quiz",
                        correct_option_id=q.get("correct", 0),
                        explanation=explanation,
                        read_timeout=30,
                        connect_timeout=30
                    )
                    log_text = question_text[:30].replace('\n', ' ')
                    print(f"Sent poll {count}/{total_questions} for {subject}: {log_text}...")
                    
                    count += 1
                    await asyncio.sleep(2)  # Delay between sending polls to prevent ratelimits/timeouts
                except Exception as e:
                    print(f"Error sending poll {count} for {subject}: {e}")

    # Send ending message
    end_message = (
        "✅ <b>Mock Test Completed!</b>\n\n"
        "Check explanations carefully.\n\n"
        "<i>⏰ Next Mock Test: Tomorrow 8:00 AM</i>"
    )
    
    promo_message = (
        "📊 <b>Want full mock tests?</b>\n\n"
        "Visit: https://iisersmartprep.space"
    )

    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=end_message,
            parse_mode="HTML",
            read_timeout=30,
            connect_timeout=30
        )
        await asyncio.sleep(2)
        
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=promo_message,
            parse_mode="HTML",
            read_timeout=30,
            connect_timeout=30
        )
        print("Sent ending and promo messages.")
    except Exception as e:
        print(f"Error sending ending messages: {e}")

if __name__ == "__main__":
    from datetime import datetime

    start_date = datetime(2026, 3, 10)
    today = datetime.now()

    day_number = (today - start_date).days + 1
    target_day = f"day{day_number}"

    print(f"Running quiz for {target_day}")
    asyncio.run(main(target_day))