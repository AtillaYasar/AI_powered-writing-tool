import json, os, time, threading
import colorsys

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import embeddings_module
# my own tkinter wrappers
from tkinter_windows import Scratchpads, EmbeddingsWindow, ChatgptPrompter, TextWithListbox

def col(ft, s):
    """For printing text with colors.
    
    Uses ansi escape sequences. (ft is "first two", s is "string")"""
    # black-30, red-31, green-32, yellow-33, blue-34, magenta-35, cyan-36, white-37
    u = '\u001b'
    numbers = dict([(string,30+n) for n, string in enumerate(('bl','re','gr','ye','blu','ma','cy','wh'))])
    n = numbers[ft]
    return f'{u}[{n}m{s}{u}[0m'

def set_tab_length(widget, length):
    font = tkfont.Font(font=widget['font'])
    tab_width = font.measure(' ' * 4)
    widget.config(tabs=(tab_width,))

class StorageManager:
    def __init__(self, widget, path):
        assert isinstance(widget, tk.Text)
        self.widget = widget
        self.path = path

        self.widget.bind('<KeyPress>', self.on_press_additions, add='+')

    def save(self):
        with open(self.path, 'w') as f:
            f.write(self.widget.get('1.0', 'end')[:-1])
        print(f'saved to {self.path}')

    def load(self):
        with open(self.path, 'r') as f:
            new = f.read()
        self.widget.delete('1.0', 'end')
        self.widget.insert('1.0', new)
        print(f'loaded from {self.path}')
    
    def on_press_additions(self, event):
        if event.keysym == 's' and event.state == 12:
            self.save()
        elif event.keysym == 'l' and event.state == 12:
            self.load()

def get_selected(text_widget):
    # returns mouse-selected text from a tk.Text widget
    try:
        text_widget.selection_get()
    except:
        return None
    else:
        return text_widget.selection_get()

class ConfigHandler:
    # main, chatgpt, embeddings, scratchpads
    default_config = {
        'meta':{
            'color 1': 'black',
            'color 2': 'cyan',
            'default font': ('comic sans', 12),
            'topleft': '+0+0',
            'topright': '-0+0',
            'bottomleft': '+0-40',
            'bottomright': '-0-40',
        },
        'main':{
            'background': '{color 1}',
            'foreground': '{color 2}',
            'insertbackground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 40,
            'height': 20,
            'geometry': '{topleft}',
            'title': 'main',
        },
        'chatgpt':{
            'background': '{color 1}',
            'foreground': '{color 2}',
            'insertbackground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 40,
            'height': 20,
            'geometry': '{bottomright}',
            'title': 'chatgpt',
        },
        'embeddings':{
            'background': '{color 1}',
            'foreground': '{color 2}',
            'insertbackground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 40,
            'height': 20,
            'geometry': '{bottomleft}',
            'title': 'embeddings',
        },
        'scratchpads':{
            'background': '{color 1}',
            'foreground': '{color 2}',
            'insertbackground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 40,
            'height': 20,
            'geometry': '{topright}',
            'title': 'scratchpads',
        },
        'listbox':{
            'background': '{color 1}',
            'foreground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 10,
            'height': 20,
        },
    }
    def __init__(self, config_path):
        self.config_path = config_path

        # for convenience
        if config_path not in os.listdir():
            with open(config_path, 'w') as f:
                json.dump(self.get_default_config(), f, indent=4)

    def apply_meta(self, settings, meta):
        new = {}
        for k,v in settings.items():
            if type(v) == str:
                if v.startswith('{') and v.endswith('}'):
                    new[k] = meta[v[1:-1]]
                else:
                    new[k] = v
            else:
                new[k] = v
        return new

    def apply_config(self, widget, settings):
        # since the config file contains geometry and title too, and possibly more things in the future, ill use this function to handle any annoying "implementation details"

        widget_type = type(widget)
        if isinstance(widget, (tk.Toplevel, tk.Tk)):
            widget.title(settings['title'])
            widget.geometry(settings['geometry'])
        elif widget_type == tk.Text:
            settings = {k:v for k,v in settings.items() if k not in ['geometry', 'title']}
            widget.config(**settings)
        elif widget_type == tk.Listbox:
            settings = {k:v for k,v in settings.items() if k not in ['geometry', 'title']}
            widget.config(**settings)
        else:
            raise Exception(f'widget type {widget_type} not supported by ConfigHandler.apply_config()')

    def get_default_config(self):
        return self.default_config

    def get_config(self):
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def reset_default(self):
        with open('default_config.json', 'w') as f:
            json.dump(self.get_default_config(), f, indent=4)

def int_to_hexadecimal(number):
    """Takes an integer between 0 and 255, returns the hexadecimal representation."""

    if number < 0 or number > 255:
        raise ValueError('must be between 0 and 255')

    digits = list("0123456789ABCDEF")
    first = number // 16
    second = number%16
    return ''.join(map(str,(digits[first],digits[second])))

def hsv_to_hexcode(hsv, scale=1):
    """Takes a list of 3 numbers, returns hexcode.

    Divides each number by scale, multiplies by 255, rounds it, converts to 2-digit hex number

    Scale divides each number to make it a fraction.
        (So with scale=500, you can pass numbers between 0 and 500, instead of between 0 and 1.)
    """
    numbers = list(map(lambda n:n/scale, (hsv)))
    rgb = colorsys.hsv_to_rgb(*numbers)
    hexcode = '#' + ''.join(map(lambda n:int_to_hexadecimal(int(n*255)), rgb))
    return hexcode

def analyze(widget):
    # start of word highlighting, inspired by https://twitter.com/InternetH0F/status/1656853851348008961

    # helper functions
    def convert_range(pair):
        """take normal range, return tkinter range"""
        assert len(pair) == 2
        assert len(pair[0]) == 2
        assert len(pair[1]) == 2
        def conv(tup):
            line, char = tup
            string = f'{line+1}.{char}'
            return string

        str1, str2 = map(conv, pair)
        tkinter_range = (str1, str2)

        return tkinter_range
    def get_hsv(color):
        rgb = tuple((c/65535 for c in widget.winfo_rgb(color)))
        hsv = colorsys.rgb_to_hsv(*rgb)
        return hsv
    def change_color(color, changers):
        # changers should be 3 callables, each taking a number between 0 and 1, and returning a number between 0 and 1
        # will be applied to hue/saturation/value, in that order.
        # (to make darker, reduce value)
        hsv = get_hsv(color)
        new_hsv = tuple(map(lambda n:changers[n](hsv[n]), range(3)))
        new_color = hsv_to_hexcode(new_hsv, scale=1)
        return new_color

    def get_changers():
        def third_fg_changer(n):
            # make darker
            n = max(0.1, n*0.7)
            return n
        fg_changers = [
            lambda n:n,
            lambda n:n,
            third_fg_changer,
        ]
        bg_changers = [
            lambda n:n,
            lambda n:n,
            lambda n:n,
        ]
        return fg_changers, bg_changers

    to_analyze = widget.get(1.0, 'end')[:-1]

    # get indices of words
    word_indices = []
    lines = to_analyze.split('\n')
    for line_n, line in enumerate(lines):
        idx = 0
        words = line.split(' ')
        for word in words:
            indices = ( (line_n,idx), (line_n,idx+len(word)) )
            word_indices.append(indices)
            idx += len(word) + 1  # +1 is for the space

    for pair in word_indices:
        ranges = convert_range(pair)
        widget.tag_add('wordstart', ranges[0], ranges[0]+' +2c')

    # keep bg the same, make fg darker.
    fg_changers, bg_changers = get_changers()
    new_fg = change_color(
        widget.cget('fg'),
        fg_changers
    )
    new_bg = change_color(
        widget.cget('bg'),
        bg_changers
    )

    widget.tag_config('wordstart', foreground=new_fg, background=new_bg)

class App:
    def __init__(self, root, config_handler):
        self.data_handler = embeddings_module.DataHandler()
        self.config_handler = config_handler
        self.root = root
        
        folder = 'editor_storage'
        if folder not in os.listdir():
            os.mkdir(folder)
        storage_paths = {
            'main': f'{folder}/main.txt',
            'chatgpt': f'{folder}/chatgpt.txt',
            'embeddings in': f'{folder}/embeddings_in.txt',
            'embeddings out': f'{folder}/embeddings_out.txt',
            'scratchpads': f'{folder}/scratchpads.json',
        }

        full_config = self.config_handler.get_config()
        meta = full_config['meta']

        scratchpads_config = self.config_handler.apply_meta(  # very clunky and bad
            full_config['scratchpads'],
            meta,
        ),
        scratchpads_window_config = {k:v for k,v in scratchpads_config[0].items() if k in ['geometry', 'title']}
        scratchpads_editor_config = {k:v for k,v in scratchpads_config[0].items() if k not in ['geometry', 'title']}

        self.main_window = TextWithListbox(root)
        self.scratchpads_window = Scratchpads(
            storage_paths['scratchpads'],
            scratchpads_editor_config,
            {},
        ) # needs path, editor settings, entry box settings
        self.chatgpt_window = ChatgptPrompter()
        self.emb_window = EmbeddingsWindow(self.data_handler)
        
        # enables saving on ctrl+s, loading on ctrl+l
        for widget, key in [
            (self.main_window.editor, 'main'),
            (self.chatgpt_window.editor, 'chatgpt'),
            (self.emb_window.inputs_editor, 'embeddings in'),
            (self.emb_window.outputs_editor, 'embeddings out'),
        ]:
            widget.storage_manager = StorageManager(widget, storage_paths[key])
            widget.storage_manager.load()

        # applying config
        for widget, key in [
            (root, 'main'),
            (self.main_window.editor, 'main'),
            (self.main_window.listbox, 'listbox'),
            (self.chatgpt_window, 'chatgpt'),
            (self.chatgpt_window.editor, 'chatgpt'),
            (self.emb_window, 'embeddings'),
            (self.emb_window.inputs_editor, 'embeddings'),
            (self.emb_window.outputs_editor, 'embeddings'),
            (self.scratchpads_window, 'scratchpads'),
        ]:
            settings = full_config[key]
            settings = self.config_handler.apply_meta(settings, meta)
            self.config_handler.apply_config(widget, settings)

        # setting tab length
        for editor in [
            self.main_window.editor,
            self.chatgpt_window.editor,
            self.emb_window.inputs_editor,
            self.emb_window.outputs_editor,
        ]:
            set_tab_length(editor, 4)

        # the Scratchpads class has a function called `fkey_bindings` that handles the behavior of, "press F-key, go to tab"
        for window in [
            root,
            self.chatgpt_window.editor,
            self.emb_window,
        ]:
            window.bind('<KeyPress>', self.scratchpads_window.fkey_bindings, add='+')

        # set up replacements code. is hacky and needs to be rewritten.
        for widget in [
            self.emb_window,
            self.chatgpt_window,
        ]:
            widget.scratchpads = self.scratchpads_window
        
        # some annoying bullshit
        self.chatgpt_window.emb_window = self.emb_window

        '''# handle hotkeys
        self.root.bind_all('<KeyPress>', self.global_keypress)

        hotkeys = {
            'chatgpt generate': 'ctrl+g',
            'chatgpt add system': 'ctrl+1',
            'chatgpt add user': 'ctrl+2',
            'chatgpt add assistant': 'ctrl+3',
            'chatgpt remove': 'ctrl+r',
            'do embsearch': 'ctrl+e',
            'feed embeddings': 'ctrl+q',
        }
        self.funcs = {
            'chatgpt generate': self.chatgpt_prompter.generate,
            'chatgpt add system': lambda string: self.chatgpt_prompter.add_message('system', string),
            'chatgpt add user': lambda string: self.chatgpt_prompter.add_message('user', string),
            'chatgpt add assistant': lambda string: self.chatgpt_prompter.add_message('assistant', string),
            'chatgpt remove': self.chatgpt_prompter.remove_message,
            'do embsearch': self.emb_window.embsearch,
            'feed embeddings': self.embed_contents,
        }'''

        root.bind_all('<KeyPress>', self.global_keypress)
        self.chatgpt_window.bind('<KeyPress>', self.chatgpt_keypress)

    def embed_contents(self, widget):
        # not multithreading this because it might go wrong when multiple threads try to edit the same files

        print(col('re', 'started embedding strings, app will freeze until its done'))

        def get_stuff():
            stuff = []
            contents = widget.get(1.0, 'end')[:-1]
            strings = contents.split('\n=====\n')
            for string in strings:
                # use !!! lines as metadata tags
                lines = []
                tags = []
                for line in string.split('\n'):
                    if line.startswith('!!!'):
                        tags.append(line[3:])
                    else:
                        lines.append(line)
                stuff.append((
                    '\n'.join(lines),
                    tags
                ))
            return stuff
        stuff = get_stuff()

        for text, tags in stuff:
            # will add the strings to the database, assigning the tags as metadata
            self.data_handler.get_embedding(
                text,
                tags,
            )

        print(col('gr', 'done embedding strings'))

    def focus_all(self):
        windows = [
            self.root,
            self.scratchpads_window,
            self.chatgpt_window,
            self.emb_window,
        ]
        for w in windows:
            w.state(newstate='normal')
            w.focus_set()
        self.main_window.editor.focus_set()
    
    def to_window(self, string):
        assert string in ['main', 'scratchpads', 'embeddings', 'chatgpt']
        if string == 'main':
            self.main_window.goto()
        elif string == 'scratchpads':
            self.scratchpads_window.goto()
        elif string == 'embeddings':
            self.emb_window.goto()
        elif string == 'chatgpt':
            self.chatgpt_window.goto()

    def get_cur_window(self):
        cur_window = self.root.focus_get()
        if cur_window == self.main_window.editor:
            return 'main'
        elif cur_window in self.scratchpads_window.f_to_widget.values():
            return 'scratchpads'
        elif cur_window == self.emb_window.inputs_editor or cur_window == self.emb_window.outputs_editor:
            return 'embeddings'
        elif cur_window == self.chatgpt_window.editor:
            return 'chatgpt'
        else:
            raise Exception(f'unknown window {cur_window}')
    
    def next_window(self):
        sequence = ['main', 'scratchpads', 'chatgpt', 'embeddings']
        string = self.get_cur_window()
        idx = sequence.index(string)
        idx += 1
        if idx >= len(sequence):
            idx = 0
        self.to_window(sequence[idx])
        
    def prev_window(self):
        sequence = ['main', 'scratchpads', 'chatgpt', 'embeddings']
        string = self.get_cur_window()
        idx = sequence.index(string)
        idx -= 1
        if idx < 0:
            idx = len(sequence) - 1
        self.to_window(sequence[idx])

    def global_keypress(self, event):
        if event.keysym == 'g' and event.state == 12:
            self.chatgpt_window.generate()
        elif event.keysym == 'Escape':
            self.focus_all()
        elif event.keysym == 'e' and event.state == 12:
            w = event.widget
            if isinstance(w, tk.Text):
                sel = get_selected(w)
                if sel == None:
                    searchterm = self.emb_window.get_search_term()
                else:
                    searchterm = sel
                search_params = self.emb_window.get_search_params()

                self.emb_window.embsearch(searchterm, search_params)
                self.emb_window.outputs_editor.focus_set()
        elif event.keysym == 'q' and event.state == 12:
            self.embed_contents(event.widget)    
        elif event.keysym == 'Next' and event.state == 262156:
            self.next_window()
        elif event.keysym == 'Prior' and event.state == 262156:
            self.prev_window()
        elif event.keysym == 'b' and event.state == 12:
            analyze(event.widget)

    def chatgpt_keypress(self, event):
        if event.keysym == '1' and event.state == 12:
            self.chatgpt_window.add_message('system', '')
        elif event.keysym == '2' and event.state == 12:
            self.chatgpt_window.add_message('user', '')
        elif event.keysym == '3' and event.state == 12:
            self.chatgpt_window.add_message('assistant', '')
        elif event.keysym == 'r' and event.state == 12:
            self.chatgpt_window.remove_message()

def main():
    root = tk.Tk()
    config_handler = ConfigHandler('config.json')
    app = App(root, config_handler)


    def extra_replacer(string):
        # uses `chatgpt_prompter` object. not good.

        chatgpt_prompter = app.chatgpt_window
        main_frame = app.main_window
    
        chatgpt_messages = chatgpt_prompter.text_to_messages(
            chatgpt_prompter.editor.get('1.0', 'end')[:-1]
        )
        chatgpt_latest = chatgpt_messages[-1]['content']
        chatgpt_full = chatgpt_prompter.messages_to_text(chatgpt_messages)
        d = {
            'main': main_frame.editor.get('1.0', 'end')[:-1],
            'chatgpt.latest': chatgpt_latest,
            'chatgpt.last': chatgpt_latest,  # just for convenience
            'chatgpt.full': chatgpt_full,
        }
        for flag, content in d.items():
            to_replace = '{' + flag.lower() + '}'
            if to_replace in string:
                string = string.replace(to_replace, content)
        return string
    app.scratchpads_window.add_replacer(extra_replacer)

    root.mainloop()

main()
