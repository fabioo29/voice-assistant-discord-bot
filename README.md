<h2 align="center">Voice assistant discord bot</h2>
<h4 align="center">Music discord bot with built-in google assistant</h4>
  
<br>
<p style="text-align: justify"><b>Bot default prefixes</b>: ['-', '!', 'google '] - The bot will recognize your voice if it starts with those prefixes or any chat command in the same way. You can see what the bot is catching in your console with the '<i>-sp</i>' argument. Check <b>Input arguments</b> below for more info.</p>

<br>

<h4><b>-help command</b> <i> (known existing google commands + some usefull ones)</i></h4>

```
Voice commands
  tell me a joke
  temperature braga {in centigrades}
  rain today lisbon
  what's python language?
  time in japan
  day in 29/04/1998
  423*12+23-1
  spin the wheel
  cristiano ronaldo {born,married, age, play for}
  who wrote rich dad poor dad
  10cm to inch
  real madrid win
  surprise me

Chat commands (+ voice commands)\n
  -translate hello {en, english} {pt, portuguese}
  -convert 100 USD EUR
  -quote AAPL
  -play {youtube url/search terms}
  -{pause, unpause, skip, queue}
```

<p></p>

<b>Input arguments</b> <i> (optional features)</i>
```shell
python discord-bot/main.py --help
usage: main.py [-h] [-sp] [-cd] [-rt RESPONSETIME]

optional arguments:
  -h, --help            show this help message and exit
  -sp, --speechdetection
                        show speech detection print in console
  -cd, --channeldialog  hide dialog User/BOT in channel chat
  -rt RESPONSETIME, --responsetime RESPONSETIME
                        time for user to ask something to BOT in voice channel
```

<br>

<b>SETUP: </b>You need to change the `.env` file according to your data:
```python
# .env file you need to change
# check .env.example for instructions

DEVICE_ID = "something-something"

DEVICE_MODEL_ID = "<DEVICE_ID>-something-something"

CREDENTIALS = '{'key1': 'value1', 'key2': 'value2'}'

ASSISTANT_TOKEN = "Token from credentials.json"

DISCORD_TOKEN = "discord Token"
```
```
virtualenv venv -p python3.9    # create virtualenv
source venv/bin/activate

# install dependencies
pip install -r requirements     
sudo apt update; sudo apt-install ffmpeg

python discord-bot/main.py      # start discord app
```  
<b>To add: </b>: (1) Top.gg integrationn  

<br>

<p align="center">Tested in Ubuntu 18.04, Python3.9</p>
  
