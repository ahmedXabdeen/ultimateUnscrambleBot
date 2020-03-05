from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging, random, time
import threading 
import os


TOKEN = os.environ['TOKEN']
bot_id = TOKEN=os.environ['BOTID']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

games = {}

words = []

with open("words.txt") as f:
    for w in f:
        words.append(w.strip())

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hi and welcome to the Ultimate Unscramble Game Bot!\n\nA bot for playing unscramble competitively in groups. Add this bot to your group to start playing.")

def players(update, context):
    chat_id = update.message.chat_id
    if chat_id not in games:
        update.message.reply_text("There's no active game, start one with /startGame")
        return
    players = games[chat_id]["players"]
    finalPlayers = {k: v for k, v in sorted(players.items(), key=lambda item: item[1]['score'], reverse=True)}
    players = [(k, v) for k, v in finalPlayers.items()]
    message = 'Players:\n'
    for item in players:
        message += f'[{item[1]["data"]["first_name"]} {item[1]["data"]["last_name"] or ""}](tg://user?id={item[1]["data"]["id"]})\n'
    update.message.reply_markdown(message)

def sendEndTimer(update, context, remaining, index):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=f"{remaining} til the end of game")
    games[chat_id]["gameEndTimers"][index+1].start()

def gameEnder(update, context, timer=False):
    chat_id = update.message.chat_id
    user = update.message.from_user
    free = games[chat_id]["mode"] == "free"
    if chat_id not in games:
        update.message.reply_text("There's no active game, start one with /startGame")
        return
    if user["id"] not in games[chat_id]["players"] and not timer:
        update.message.reply_text("STHU you ain't even playin...")
        return
    games[chat_id]["active"] = False
    timers = games[chat_id]["gameEndTimers"]
    for item in timers:
        if(hasattr(item, 'cancel')):
            item.cancel()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'The correct word is {games[chat_id]["correct"]}')
    if not free:
        games[chat_id]["timer"].cancel()
    players = games[chat_id]["players"]
    context.bot.send_message(chat_id=chat_id, text="Ending this game session, calculating scores...")
    finalPlayers = {k: v for k, v in sorted(players.items(), key=lambda item: item[1]['score'], reverse=True)}
    players = [(k, v) for k, v in finalPlayers.items()]
    if(len(players)):
        winner = players[0]
        if(winner[1]["score"] == 0):
            message = "There's no winner\n\nplayers:\n"
        else:
            message = f'The Winner is [{winner[1]["data"]["first_name"]} {winner[1]["data"]["last_name"] or ""}](tg://user?id={winner[1]["data"]["id"]})\nscore: {winner[1]["score"]}\n\nPlayers:\n'
        for item in players:
            message += f'{item[1]["data"]["first_name"]} {item[1]["data"]["last_name"] or ""}: {item[1]["score"]}\n'

        elapsed_time = time.time() - games[chat_id]["start_time"]
        duration = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        message += f"\nGame duration: {duration}"
        update.message.reply_markdown(message)
    else:
        update.message.reply_text('What a shame! Nobody played in this game...')
    del games[chat_id]

def pauseGame(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    free = games[chat_id]["mode"] == "free"
    if chat_id not in games:
        update.message.reply_text("There's no active game, start one with /startGame")
        return
    if user["id"] not in games[chat_id]["players"] and not timer:
        update.message.reply_text("STHU you ain't even playin...")
        return

    # set game status to NOT active
    games[chat_id]["active"] = False

    # cancel game end timers 
    timers = games[chat_id]["gameEndTimers"]
    for item in timers:
        if(hasattr(item, 'cancel')):
            item.cancel()

    # solving the word
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'The correct word is {games[chat_id]["correct"]}')
    games[chat_id]["solved"] = True

    # cancelling the word time out timer
    if not free:
        games[chat_id]["timer"].cancel()

    # note call setAndSendWord() on resume 

def resumeGame(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    free = games[chat_id]["mode"] == "free"

    # check if user is permitted to resume
    if user["id"] not in games[chat_id]["players"] and not timer:
        update.message.reply_text("STHU you ain't even playin...")
        return

    # change game status to active
    games[chat_id]["active"] = True

    # call setAndSendWord(), that automatically sets the word time out timers
    setAndSendWord(update, context, free)
    
    # set game end timers
    games[update.message.chat_id]["gameEndTimers"] = [
                threading.Timer(60, sendEndTimer, args=(update,context,'two minutes',0)),
                threading.Timer(60, sendEndTimer, args=(update,context, 'one minute', 1)),
                threading.Timer(30, sendEndTimer, args=(update,context, '30 seconds', 2)),
                threading.Timer(20, sendEndTimer, args=(update,context, '10 seconds', 3)),
                threading.Timer(10, gameEnder, args=(update,context, True)),
            ]
    games[chat_id]["gameEndTimers"][0].start()
    


def wordTimeOut(update, context, solve=False):
    chat_id = update.message.chat_id
    games[chat_id]["solved"] = True
    if solve:
        update.message.reply_text(f'The correct word is {games[chat_id]["correct"]}')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'The correct word is {games[chat_id]["correct"]}')
    return setAndSendWord(update, context, free=solve)

def setAndSendWord(update, context, free=False):
    chat_id = update.message.chat_id
    if games[chat_id]["solved"] and games[chat_id]["active"]:
        new_w = list(random.choice(words))
        games[chat_id]["correct"] = "".join(new_w)

        random.shuffle(new_w)
        games[chat_id]["current"] = "".join(new_w)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"The word to solve is: \n{games[chat_id]['current']}")

        games[chat_id]["solved"] = False
        if not free:
            games[chat_id]["timer"] = threading.Timer(25.0, wordTimeOut, args=(update,context))
            games[chat_id]["timer"].start()

def welcome_group_addition(update, context):
    new_members = update.message.new_chat_members
    for member in new_members:
        if(member.id==bot_id):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! You just added the Ultimate Unscramble Game bot to your group. \n\nTo start a game, just use the /startGame command and start solving!\n\nBy continuing to use this bot, you are agreeing to the /terms of service. Enjoy!")
            

def checkGroupAddition(update, context):
    if(len(update.message.new_chat_members)):
        return welcome_group_addition(update, context)

def checkSolution(update, context):
    chat_id = update.message.chat_id
    free = games[chat_id]["mode"] == "free"
    if chat_id in games and games[chat_id]["active"]:
        solution = update.message.text.strip().split()[0]
        user = update.message.from_user
        if(not games[chat_id]["solved"] and solution.lower()==games[chat_id]["correct"].lower()):
            games[chat_id]["solved"] = True
            if not free:
                games[chat_id]["timer"].cancel()
            update.message.reply_markdown(f'[{user["first_name"]} {user["last_name"] or ""}](tg://user?id={user["id"]})  solved the word 🥳🥳')
            if user["id"] not in games[chat_id]["players"]:
                games[chat_id]["players"][user['id']] = {"score":0, "data":user}
            games[chat_id]["players"][user["id"]]["score"] += 1
            return setAndSendWord(update, context, free)

def extendGameTime(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    if chat_id not in games:
        update.message.reply_text("There's no active game, start one with /startGame")
        return
    if user["id"] in games[chat_id]["players"]:
        timers = games[chat_id]["gameEndTimers"]
        for item in timers:
            if(hasattr(item, 'cancel')):
                item.cancel()
        update.message.reply_text("Game time extended. You can /end the game when/if you feel like it.")
        games[update.message.chat_id]["gameEndTimers"] = [
                    threading.Timer(60, sendEndTimer, args=(update,context,'two minutes',0)),
                    threading.Timer(60, sendEndTimer, args=(update,context, 'one minute', 1)),
                    threading.Timer(30, sendEndTimer, args=(update,context, '30 seconds', 2)),
                    threading.Timer(20, sendEndTimer, args=(update,context, '10 seconds', 3)),
                    threading.Timer(10, gameEnder, args=(update,context, True)),
                ]
        games[chat_id]["gameEndTimers"][0].start()
    else:
        update.message.reply_text("STHU you ain't even playin...")
     
def gameStarter(update, context, free=False):
    chat_id = update.message.chat_id
    games[update.message.chat_id]["active"] = True
    games[update.message.chat_id]["gameEndTimers"] = [
                threading.Timer(60, sendEndTimer, args=(update,context,'two minutes',0)),
                threading.Timer(60, sendEndTimer, args=(update,context, 'one minute', 1)),
                threading.Timer(30, sendEndTimer, args=(update,context, '30 seconds', 2)),
                threading.Timer(20, sendEndTimer, args=(update,context, '10 seconds', 3)),
                threading.Timer(10, gameEnder, args=(update,context, True)),
            ]
    games[chat_id]["gameEndTimers"][0].start()
    update.message.reply_text('Starting game... Buckle Up!\n\nGame duration is 3 minutes, you can always /extend game time tho')
    return setAndSendWord(update, context, free)


def startGame(update, context):

    chat_id = update.message.chat_id
    user = update.message.from_user

    if chat_id not in games:
        games[chat_id] = {
            "mode": "normal",
            "current": "", 
            "correct": "", 
            "solved": True, 
            "active": False, 
            "players": {},
            "start_time": time.time()
        }
        # add whoever it's who started the game to players 
        games[chat_id]["players"][user['id']] = {"score":0, "data":user}
        gameStarter(update,context)

def startFreeGame(update, context):
    chat_id = update.message.chat_id
    if chat_id not in games:
        games[chat_id] = {
            "mode": "free",
            "current": "", 
            "correct": "", 
            "solved": True, 
            "active": False, 
            "players": {},
            "start_time": time.time()
        }
        gameStarter(update, context, free=True)

def solve(update, context):
    chat_id = update.message.chat_id

    if chat_id in games and games[chat_id]["mode"] == "free":
        wordTimeOut(update, context, solve=True)



def terms(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='markdown', text='*Terms of Service:* \n\nI hereby agree to send @ahmedXabdeen a bag of homemade cookies whenever he asks for them.')

start_handler = CommandHandler('start', start)
terms_handler = CommandHandler('terms', terms)
end_handler = CommandHandler('end', gameEnder)
players_handler = CommandHandler('players', players)
startGame_handler = CommandHandler('startGame', startGame)
startFreeGame_handler = CommandHandler('startFreeGame', startFreeGame)
extendGameTime_handler = CommandHandler('extend', extendGameTime)
solve_handler = CommandHandler('solve', solve)
pauseGame_handler = CommandHandler('pause', pauseGame)
resumeGame_handler = CommandHandler('resume', resumeGame)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(terms_handler)
dispatcher.add_handler(end_handler)
dispatcher.add_handler(players_handler)
dispatcher.add_handler(startGame_handler)
dispatcher.add_handler(startFreeGame_handler)
dispatcher.add_handler(solve_handler)
dispatcher.add_handler(extendGameTime_handler)
dispatcher.add_handler(pauseGame_handler)
dispatcher.add_handler(resumeGame_handler)
dispatcher.add_handler(MessageHandler(Filters.text, checkSolution))
dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, checkGroupAddition), group=9)

updater.start_polling()
updater.idle()