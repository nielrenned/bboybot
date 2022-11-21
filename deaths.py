import socket
import select
import sys
import traceback

'''

To run: type "python deaths.py" at the cmd prompt.

This is built for Python 3, but _should_ work in Python 2 also. I haven't tested it.

The class TwitchChatBot handles all the basics: connecting to server, handling
commands, sending messages, etc.
The class BBoyDeathsBot inherits from TwitchChatBot and implements a !deaths 
command that works as follows:
  For mods/broadcaster only:
   - Type "!deaths open" to open guessing.
   - Type "!deaths close" to close guessing.
   - Type "!deaths reset" to erase all guesses. This allows guessing to be 
     closed, and then re-opened without losing guesses.
   - Type "!deaths restore" to restore the previous set of guesses. This is 
     here in case someone resets the guesses by accident.
   - Type "!deaths check <number>" to see if anyone got the correct guess.
     This will output all winning users, or if no one got it right, will
     output the ones who were closest.
  For anyone:
   - Type "!deaths <number>" to register a guess.
   - Type "!deaths update <number>" to change a guess.
  Other info:
   - Everything is running on the main thread, which makes the program a little
     unresponsive. To stop it, press Ctrl-C and it will exit within 1 second.
   - On exit, the guesses are saved in the working directory in guesses.txt,
     which is reloaded on the next program startup.
    
To connect to Twitch Chat, the bot needs an OAuth token and the account
name. You can use the one I've included here (nielbot) if you'd like. If not,
making the OAuth token is very easy. Just be sure to do it from the correct
account.

Feel free to PM me on Discord with any questions, or if you want me to make
any changes.

- nielrenned

'''

OAUTH_TOKEN  = ''
ACCOUNT_NAME = ''
CHANNEL      = '#bounceyboy'

class TwitchChatBot:
    def __init__(self, token, account_name, channel_name):
        self.irc = socket.socket()
        self.oauth_token = token
        self.account_name = account_name
        self.channel_name = channel_name
        self.errors = []
        self.commands = {}
    
    def send_message(self, message):
        self.send_raw('PRIVMSG {} :{}'.format(self.channel_name, message))
    
    def send_raw(self, raw_message):
        self.irc.sendall((raw_message + '\r\n').encode('utf-8'))
    
    def receive(self, num_bytes, timeout=1):
        if timeout != 0:
            ready = select.select([self.irc], [], [], timeout)
            if ready[0]:
                return self.irc.recv(num_bytes).decode('utf-8')
            else:
                return ''
        else:
            return self.irc.recv(num_bytes).decode('utf-8')
    
    def start_chatting(self):
        self.irc.connect(('irc.chat.twitch.tv', 6667))
        # This is how Twitch requires we "introduce" ourselves to the chatroom
        self.send_raw('PASS {}'.format(self.oauth_token))
        self.send_raw('NICK {}'.format(self.account_name))
        self.send_raw('JOIN {}'.format(self.channel_name))
        # This is telling Twitch what info we want to be sent with each message.
        self.send_raw('CAP REQ :twitch.tv/tags')
        self.send_raw('CAP REQ :twitch.tv/membership')
        self.send_raw('CAP REQ :twitch.tv/commands')
        
        # This is the format of the message we get with a successful connection.
        ready_message = ':{0}!{0}@{0}.tmi.twitch.tv JOIN {1}'.format(self.account_name, self.channel_name)
        
        # Loop forever, waiting on messages.
        # This should probably be in another thread, but it seems to be working alright.
        prepend = '' # This is used in case a line gets split in the middle of a received message
        line = None
        while True:
            try:
                response = self.receive(1024)
                lines = response.split('\r\n')
                lines[0] = prepend + lines[0]
                # Ignore last line, in case it was cut in half
                prepend = lines[-1]
                for line in lines[:-1]:
                    # Weird IRC thing that is checking if you're alive
                    if line == 'PING :tmi.twitch.tv':
                        self.send_raw('PONG :tmi.twitch.tv')
                    elif line == ready_message:
                        print('Connected.')
                    else:
                        self.parse_raw_message(line)
            except:
                info = sys.exc_info()
                self.errors.append((line, info))
                if info[0] is KeyboardInterrupt:
                    self.stop_chatting()
                    break
                print(line)
                print(traceback.format_exc())
    
    def stop_chatting(self):
        self.send_raw('PART {}'.format(self.channel_name))
        self.irc.close()
    
    def parse_tags(self, tags_string):
        if tags_string is None:
            return {}
        tags = {}
        tags_string = tags_string.strip()
        if len(tags_string) == 0:
            return tags
        if tags_string[0] != '@':
            return tags
        tags_list = tags_string[1:].split(';')
        for tag in tags_list:
            name, value = tag.split('=')
            tags[name] = value
        return tags
    
    def parse_badges(self, tags):
        if 'badges' not in tags:
            return {}
        badges_string = tags['badges']
        if len(badges_string) == 0:
            return []
        badge_strings = badges_string.split(',')
        badges = {}
        for badge_str in badge_strings:
            #print(badge_str)
            badge, count = badge_str.split('/')
            badges[badge] = count
        return badges
    
    def parse_spaces(self, s):
        return s.replace('\\s', ' ').strip()
    
    def parse_raw_message(self, raw_message):
        tags_string = None
        message_type = None
        message_text = None
        sending_user = None
        
        hash_loc = raw_message.find(self.channel_name)
        if hash_loc == -1:
            if raw_message.startswith(':tmi.twitch.tv'):
                pass # message from IRC server, do nothing
            elif 'WHISPER' in raw_message:
                # whisper to bot, could ignore
                colon_loc = raw_message.find(':', raw_message.find(self.account_name))
                prev_colon_loc =  raw_message.rfind(':', 0, colon_loc-1)
                message_type = 'WHISPER'
                message_text = raw_message[colon_loc+1:]
                tags_string = raw_message[:prev_colon_loc]
            else:
                return
        else:
            tags_end = raw_message.rfind(':', 0, hash_loc)
            tags_string = raw_message[:tags_end]
            
            prev_space = raw_message.rfind(' ', 0, hash_loc-1)
            message_type = raw_message[prev_space+1:hash_loc-1]
        
        tags = self.parse_tags(tags_string)
        
        # There are many other types of messages, but this PRIVMSG is the only one we care about for this use case.
        # If you want to learn more: https://dev.twitch.tv/docs/irc/tags
        # If we want to allow commands to be whispered to the bot (seems like a bad idea), we would include
        # that here
        if message_type == 'PRIVMSG':
            message_text = raw_message[raw_message.find(':', hash_loc)+1:]
            if message_text[0] == '\x01':
                if message_text[1:7] == 'ACTION':
                    # They typed /me, just ignore that part
                    message_text = message_text[8:-1]
            self.process_message(tags, message_text)
    
    def process_message(self, tags, text):
        display_name = self.parse_spaces(tags['display-name'])
        #print('{}: {}'.format(display_name, text))
        first_word = text.split()[0]
        if first_word in self.commands:
            callback = self.commands[first_word]
            callback(tags, text)
    
    # Callback must accept exactly two arguments: tags, text
    def register_command(self, command_name, callback):
        self.commands[command_name] = callback



class BBoyDeathsBot(TwitchChatBot):
    def __init__(self, token, account_name, channel_name):
        super(BBoyDeathsBot, self).__init__(token, account_name, channel_name)
        self.register_command('!deaths', self.deaths_command)
        self.guesses_open = False
        self.guesses = {}
        self.prev_guesses = None
        self.load_guesses()
    
    def log(self, message, fancy=False):
        if fancy:
            s = '-'*(len(message)+2)
            print(s)
            print('|' + message + '|')
            print(s)
        else:
            print(message)
    
    def stop_chatting(self):
        super(BBoyDeathsBot, self).stop_chatting();
        self.save_guesses()
    
    def save_guesses(self):
        with open('guesses.txt', 'w') as f:
            for person in self.guesses:
                guess = self.guesses[person]
                _ = f.write('{}:{}\n'.format(person, guess))
    
    def load_guesses(self):
        lines = None
        try:
            with open('guesses.txt', 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return
        for line in lines:
            if len(line) == 0:
                continue
            
            pieces = line.strip().split(':')
            if len(pieces) != 2:
                continue # This shouldn't happen
            
            name = pieces[0]
            guess_str = pieces[1]
            if not guess_str.isdigit():
                continue # This shouldn't happen
            
            self.guesses[name] = int(guess_str)
    
    def check_deaths(self, number):
        winners = []
        nearest_users = []
        best_delta = float('inf')
        for person in self.guesses:
            guess = self.guesses[person]
            if guess == number:
                winners.append(person)
            elif abs(guess - number) < best_delta:
                # reset nearest_users
                nearest_users = [(person, guess)]
                best_delta = abs(guess - number)
            elif abs(guess - number) == best_delta:
                nearest_users.append((person, guess))
        
        if len(winners) > 0:
            if len(winners) > 1:
                self.send_message('The winning users are: ' + ', '.join(winners))
            else:
                self.send_message('The winning user is: ' + winners[0])
        elif len(nearest_users) > 0:
            nearest_string = ''
            for person, guess in sorted(nearest_users, key=lambda x: (x[1], x[0])):
                nearest_string += '{} ({}), '.format(person, guess)
            nearest_string = nearest_string[:-2]
            
            if len(nearest_users) > 1:
                self.send_message('No one guessed correctly. The closest were {}.'.format(nearest_string))
            else:
                self.send_message('No one guessed correctly. The closest was {}.'.format(nearest_string))
        else:
            self.send_message('No guesses registered.')
    
    def deaths_command(self, tags, text):
        args = list(map(str.lower, text.split()))
        #print(args)
        badges = self.parse_badges(tags)
        
        is_privileged_user = False
        # Check for pleb
        if int(tags['mod']) == 1 or 'broadcaster' in badges:
            is_privileged_user = True
        
        # They just typed "!deaths"
        if len(args) == 1:
            message = None
            if self.guesses_open:
                message = 'Guessing is currently open! Type "!deaths <number>" to guess the number of times bboy will die in the next finished run. Winning user(s) get a free sub!'
            else:
                message = 'Guessing is currently closed. Please wait until the next run starts.'
            self.send_message(message)
            return
        
        failed_command = False
        
        if args[1].isdigit():
            if self.guesses_open:
                display_name = self.parse_spaces(tags['display-name'])
                if display_name not in self.guesses:
                    guess = int(args[1])
                    self.guesses[display_name] = guess
                    self.log('{} guessed {}.'.format(display_name, guess))
                    self.send_message("{}'s guess recorded: {}".format(display_name, guess))
                else:
                    self.send_message('{}, you already guessed {}! Use "!deaths update <number>" to change your guess.'.format(display_name, self.guesses[display_name]))
            else:
                self.send_message('Guessing is currently closed. Please wait until the next run starts.')
            return
        elif args[1] == 'update':
            if len(args) < 3:
                self.send_message('Usage: "!deaths update <number>"')
                return
            # Once we get here, we know args[2] exists  
            if args[2].isdigit():
                if self.guesses_open:
                    display_name = self.parse_spaces(tags['display-name'])
                    if display_name in self.guesses:
                        guess = int(args[2])
                        self.guesses[display_name] = guess
                        self.log('{} updated guess to {}.'.format(display_name, guess))
                        self.send_message("{}'s guess updated: {}".format(display_name, guess))
                    else:
                        self.send_message('{}, you need to use !deaths <number> to make your initial guess.'.format(display_name))
                else:
                    self.send_message('Guessing is currently closed. Please wait until the next run starts.')
                return
            else:
                self.send_message('Invalid argument: {}'.format(args[2]))
                return
        
        # Mod-only parts of the command
        if is_privileged_user:
            if args[1] == 'open' or args[1] == 'start':
                self.guesses_open = True
                self.log('Guessing opened.', fancy=True)
                self.send_message('Guessing is open.')
                return
            elif args[1] == 'close' or args[1] == 'stop':
                self.guesses_open = False
                self.log('Guessing closed.', fancy=True)
                self.send_message('Guessing is closed.')
                return
            elif args[1] == 'reset':
                self.prev_guesses = self.guesses
                self.guesses = {}
                self.log('Guesses reset.', fancy=True)
                self.send_message('Guessing has been reset.')
                return
            elif args[1] == 'restore':
                self.guesses = self.prev_guesses
                self.log('Guesses restored.', fancy=True)
                self.send_message('Previous guesses has been restored.')
                return
            elif args[1] == 'check':
                if len(args) != 3:
                    self.send_message('Usage: !deaths check <number>')
                    return
                if not args[2].isdigit():
                    self.send_message('Usage: "!deaths check <number>"')
                    return
                number = int(args[2])
                self.check_deaths(number)
                return
        
        # We always return on something successful, so this is the only case where it will fail
        self.send_message('Invalid argument: {}'.format(args[1]))

def main():
    bot = BBoyDeathsBot(OAUTH_TOKEN, ACCOUNT_NAME, CHANNEL)
    bot.start_chatting()

if __name__ == '__main__':
    main()