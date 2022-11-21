# Twitch Bot for Bounceyboy

This was written for the (now inactive) Twitch streamer [bounceyboy](https://www.twitch.tv/bounceyboy) in 2020. At the time, he was playing a Super Mario Sunshine challenge run, and wanted a game where the chat would guess how many times Mario died during the run.

The file contains two classes. The base class, `TwitchChatBot`, provides the functionality to connect to Twitch chat and process the formatting of messages. The class `BBoyDeathsBot` inherits from `TwitchChatBot` and provides the command used to play the guessing game.