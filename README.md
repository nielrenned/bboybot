# Twitch Bot for Bounceyboy

This was written for the (now inactive) Twitch streamer [bounceyboy](https://www.twitch.tv/bounceyboy) in 2020. At the time, he was playing a Super Mario Sunshine challenge run, and wanted a game where the chat would guess how many times Mario died during the run.

The file contains two classes. The base class, `TwitchChatBot`, provides the basic functionality to connect to Twitch chat and process the formatting of messages. The class `BBoyDeathsBot` inherits from `TwitchChatBot` and provides the command (`!deaths`) used to play the guessing game. You can see the bot in action [here](https://www.twitch.tv/videos/620184149?t=02h19m51s), under the username `honeyskipmaster`. It shows the four users who correctly guessed 35 deaths.