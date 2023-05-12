from secret_things import openai_key
import requests, json, time, os
from storage_stuff import PersistenceABC, Cache
from overall_imports import open_json, make_json

def _check_moderation(prompt):
    """Will check with the moderation endpoint whether a prompt is "safe" or not.
    
    returns
    {
        'flagged':bool,
        'per category':category:{
            'flagged':bool,
            'score':float,
        }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_key}"
    }

    # input is the text to check the safety of
    data = {'input': prompt}
    
    # call OpenAI's moderation endpoint
    response = requests.post('https://api.openai.com/v1/moderations', headers=headers, json=data).json()

    # extract safety scores and flags into something nicer.
    categories = response['results'][0]['categories']
    scores = response['results'][0]['category_scores']
    flagged = response['results'][0]['flagged']
    per_category = {}
    for k,v in categories.items():
        flagged_bool = v
        score = round(scores[k], 3)
        per_category[k] = {'flagged':flagged_bool, 'score':score}
        
    return {
        'flagged':flagged,
        'per category':per_category,
    }

def use_chatgpt(messages, detailed_response=False):
    """Use the OpenAI chat API to get a response."""

    folder_to_dump = 'chatgpt_responses'

    assert type(messages) is list
    for i in messages:
        assert type(i) is dict
        assert 'role' in i
        assert 'content' in i
        assert i['role'] in ['user', 'system', 'assistant']

    # create the request
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_key}"
    }
    data = {
        "model":"gpt-3.5-turbo",
        'messages':messages,
        'n':1,
        'temperature':0,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data)).json()

    # detect errors
    if 'error' in response:
        print('ERROR:', response['error'])
        return None
    
    if folder_to_dump != None:
        # store the data and response for debugging
        if folder_to_dump not in os.listdir():
            os.mkdir(folder_to_dump)
        make_json({'data':data, 'response':response}, f'{folder_to_dump}/{time.time()}.json')

    prompt_tokens = response['usage']['prompt_tokens']
    completion_tokens = response['usage']['completion_tokens']
    total_tokens = response['usage']['total_tokens']
    ai_response = response['choices'][0]['message']['content']
    # parse and return ai response
    if detailed_response == True:
        return {
            'prompt_tokens':prompt_tokens,
            'completion_tokens':completion_tokens,
            'total_tokens':total_tokens,
            'ai_response':ai_response,
        }
    else:
        return ai_response

def create_messages(tuples):
    """Given a list of tuples, will return a list of messages for use with OpenAI chat API."""

    messages = []
    for i in tuples:
        messages.append({
            'role': i[0],
            'content': i[1],
        })
    return messages

def token_guesser(text):
    """Given text, will guess the token count"""
    factor = 1.5  # real value is around 1.22
    words = text.split(' ')
    return int(len(words) * factor)

class Chatbot:
    """For gpt-3.5-turbo, makes context management and API calls easier.

    Methods:
    (most important one is `talk_to_bot()`)
        - add_message(tuple): tuple=(role, content), adds this to the conversation
        - check_if_safe(): check OAI moderation endpoint
        - use_api(): get the next 'assistant' message
        - go_back(): removes the last message
        - guess_tokens().
        - talk_to_bot(role, message, automod=True)
            - add 'user' message to conversation
            - check with moderation endpoint
            - if not flagged:
                - use_api()
                - add 'assistant' message to conversation
                - return response
            else:
                - go_back()
                - dont use api
    """

    def __init__(self, unique_id):
        self.unique_id = unique_id
        self.messages = []
        self.tts_handler = None
        self.cacher_object = None

        print(f'bot initialized, unique_id:{unique_id}')
        
    def add_message(self, role, message):
        """Add a message to the 'conversation' """

        for condition, rejection in (
            (
                role in ['user','assistant','system'],
                'role not allowed',
            ),
            (
                type(role) is str,
                'role must be string',
            ),
            (
                type(message) is str,
                'message must be string',
            )
        ):
            if condition == False:
                return rejection

        self.messages.append({
            'role':role,
            'content':message,
        })
    
    def check_if_safe(self):
        """Checks if the conversation follows OpenAI guidelines.

        Returns True if safe, False if not.
        """

        mod = _check_moderation(self.get_messages_as_string())
        if mod['flagged']:
            return False
        else:
            return True

    def use_api(self):
        """
        Use API to generate a response.
        """

        if self.messages == []:
            print('no context, canceling api call')
            return None
        
        input_args = self.messages
        cacher = self.cacher_object

        if cacher == None:
            print('no cacher, using api')
            api_response = use_chatgpt(input_args)
        else:
            print('using cacher')
            cached = cacher.get(input_args)
            if cached == None:
                print('not cached, using api')
                api_response = use_chatgpt(input_args)
                cacher.add(
                    input_args,
                    api_response,
                )
            else:
                print('cached, using cached')
                api_response = cached
        
        return api_response

    def get_messages_as_string(self):
        """Will return the 'conversation' converted to a string.
        (mostly for check_moderation, since that takes a string)

        Example return
            --
            role: system
            content: You are a garbage-ass chatbot.

            role: user
            content: how to get "hello world" in python?

            role: assistant
            content: I don't know :(  I suck ass.

            role: user
            content: lmao

            role: assistant
            content: Don't laugh!
        """

        assembled = '\n\n'.join('\n'.join([f'{k}: {v}' for k,v in item.items()]) for item in self.messages)
        return assembled

    def go_back(self):
        """Remove the last message."""
        self.messages = self.messages[:-1]

    def guess_tokens(self):
        as_string = self.get_messages_as_string()
        words = as_string.split(' ')
        tokens_per_word = 1.5
        return words*tokens_per_word

    def talk_to_bot(self, role, message, automod=True):
        """Add user or system message, get API response, add that one too."""

        assert role in ['user', 'system']
        self.add_message(role, message)
        if automod:
            if self.check_if_safe() == False:
                self.go_back()
                print('moderation stopped the conversation')
                return ['failed', 'moderation stopped the conversation']
            else:
                bot_response = self.use_api()
                self.add_message('assistant', bot_response)
                return ['success', bot_response]

    def add_tts_handler(self, handler):
        """
        Let the bot speak.
        The handler must have be able to do this:
            path = tts_handler.get_tts('This tts is actually working holy crap')
            tts_handler.play_tts(path)
        """

        self.tts_handler = handler
    
    def add_caching(self, cacher_object):
        """
        Add caching for bot responses.
            - cacher.get(input_args) -> output
            - cacher.add(input_args, output)
        """

        self.cacher_object = cacher_object

    def simple_loop(self, memory=[]):
        """Simple loop to test the chatbot."""

        cb = self
        for item in memory:
            cb.add_message(item['role'], item['content'])
        while True:
            possible_commands = {
                'add': 'add a user message',
                'back': 'go back one message',
                'show': 'show all messages',
                'retry': 'retry the last api call',
                'api': 'use the api, show response, and add it to the messages',
                'tts last': 'play the last message as tts',
                'help': 'show this message',
                'exit': 'exit the loop, and return to the main program',
            }
            print(f'possible commands: {list(possible_commands.keys())}')
            command = input('command: ')
            if command == 'api':
                resp = cb.use_api()
                cb.add_message('assistant', resp)
                print(f'api response: {resp}')
            elif command == 'show':
                print('-'*20)
                print(cb.get_messages_as_string())
                print('-'*20)
            elif command == 'retry':
                cb.go_back()
                cb.use_api()
                print(f'api response: {resp}')
            elif command == 'tts last':
                last_item = cb.messages[-1]
                if last_item['role'] == 'assistant':
                    if self.tts_handler is None:
                        print('no tts handler set')
                    else:
                        path = self.tts_handler.get_tts(last_item['content'])
                        self.tts_handler.play_tts(path)
                else:
                    print('last item is not from assistant')
            elif command == 'back':
                cb.go_back()
            elif command.startswith('add'):
                content = command.partition('add ')[2]
                cb.add_message('user', content)
            elif command == 'help':
                print('\n'.join([f'{k}: {v}' for k, v in possible_commands.items()]))
            elif command == 'exit':
                print('exiting')
                break
            else:
                print('invalid command')
    
    def reset(self):
        """Reset the messages."""
        self.messages = []

def summarize_conversation(messages, prompt_key):
    """Use API to summarize conversation (in messages)."""

    summarization_prompts = {
        'from user': (
            'user',
            'so you have a limited context window, and i need you to occasionally summarize what weve talked about and what your job is, etc., so i can create a new instance of you with that summary in your new memory. can you do that right now?\nwrite it as a message to a future instance of yourself.'
        ),
        'from system': (
            'system',
            'Attention: your context limit is reaching its maximum. Please summarize the current conversation, so that a future assistant can take over from here.'
        )
    }
    assert prompt_key in summarization_prompts
    role, content = summarization_prompts[prompt_key]
    messages.append({
        'role': role,
        'content': content,
    })
    summary = use_chatgpt(messages)
    return summary

class ChatbotManager:
    """
    methods:
        add_bot -- pass a unique id to add a chatbot
        find_bot -- unique id --> None or chatbot
        find_bot_by_search -- params dictionary --> list of chatbots
    """
    
    def __init__(self):
        self.chatbots = {}
        
    def add_bot(self, unique_id):
        "Returns True if it successfully added the bot, False if not."

        if unique_id in self.chatbots:
            return False
        else:
            self.chatbots[unique_id] = Chatbot(unique_id)
            return True
    
    def delete_bot(self, unique_id):
        "Returns True if it successfully deleted the bot, False if not."

        if unique_id in self.chatbots:
            del self.chatbots[unique_id]
            return True
        else:
            return False

    def find_bot(self, unique_id):
        "Returns a Chatbot object if it was found, None if not."
        
        if unique_id in self.chatbots:
            return self.chatbots[unique_id]
        else:
            return None

    def find_bot_by_search(self, params):
        # rewrite to return a list by default.
        """
        Returns a list of bots that match the search.

        params dictionary keys:
            example:
                params = {
                    'general match': 'hello world',
                    'role match': ('user', 'how to get "hello world" in python?')
                }
            explanation of keys and values:
                - overall match: str
                    will turn the bot's messages into a pure string, and search for a match.
                - role match: tuple
                    will search for a specific role's content.
        """

        for k in params.keys():
            if k not in ['general match', 'role match']:
                raise ValueError('invalid key in params dictionary')

        context_matcher = params.get('general match', None)
        role_matcher = params.get('role match', None)

        result_list = []

        for bot in self.chatbots.values():
            # search stringified context
            as_string = bot.get_messages_as_string()
            if context_matcher != None:
                if context_matcher in as_string:
                    result_list.append(bot)
                    continue

            # search specific role's content
            if role_matcher != None:
                for message in bot.messages:
                    if message['role'] == role_matcher[0]:
                        if message['content'] == role_matcher[1]:
                            result_list.append(bot)
                            break

        return result_list
    
    def create_successor(self, chatbot_object):
        """create a "successor" of a chatbot. By:
            - summarizing the current conversation
            - creating a new chatbot object with the summary in its messages
        """

        cb = chatbot_object
        assert type(cb) is Chatbot, 'chatbot_object must be of class Chatbot'

        summary = summarize_conversation(cb.messages, 'from user')
        ID = cb.unique_id
        self.delete_bot(ID)
        self.add_bot(ID)
        new_bot = self.find_bot(ID)
        new_bot.add_message('assistant', summary)
        print(f'successor of {cb.unique_id} created')

