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

    for subject in subjects:
        if subject in quiz:
            for q in quiz[subject]:
                try:
                    question = q.get("question", "No question")
                    if len(question) > 300:
                        question = question[:297] + "..."
                        
                    options = q.get("options", ["A", "B", "C", "D"])
                    options = [opt[:97] + "..." if len(opt) > 100 else opt for opt in options]
                    
                    explanation = q.get("explanation", "")
                    if len(explanation) > 200:
                        explanation = explanation[:197] + "..."
                        
                    await bot.send_poll(
                        chat_id=CHANNEL_ID,
                        question=question,
                        options=options,
                        type="quiz",
                        correct_option_id=q.get("correct", 0),
                        explanation=explanation,
                        read_timeout=30,
                        connect_timeout=30
                    )
                    print(f"Sent poll for {subject}: {question[:30]}...")
                    await asyncio.sleep(2)  # Delay between sending polls to prevent ratelimits/timeouts
                except Exception as e:
                    print(f"Error sending poll for {subject}: {e}")

if __name__ == "__main__":
    from datetime import datetime

    day_number = datetime.now().day
    target_day = f"day{day_number}"

    print(f"Running quiz for {target_day}")
    asyncio.run(main(target_day))