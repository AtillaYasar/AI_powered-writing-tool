import json, os, time, threading

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from scratchpads_class import Scratchpads
import chatgpt_stuff
import embeddings_module

def col(ft, s):
    """For printing text with colors.
    
    Uses ansi escape sequences. (ft is "first two", s is "string")"""
    # black-30, red-31, green-32, yellow-33, blue-34, magenta-35, cyan-36, white-37
    u = '\u001b'
    numbers = dict([(string,30+n) for n, string in enumerate(('bl','re','gr','ye','blu','ma','cy','wh'))])
    n = numbers[ft]
    return f'{u}[{n}m{s}{u}[0m'

# executes a given function on a new thread, so that the app doesn't freeze while it is running
def new_thread(function):
    threading.Thread(target=function).start()

def get_flagged(string, flag):
    if f'[{flag}]' in string and f'[/{flag}]' in string:
        flagged = string.partition(f'[{flag}]')[2].partition(f'[/{flag}]')[0][1:-1]
        return flagged
    else:
        return None

def set_tab_length(widget, length):
    font = tkfont.Font(font=widget['font'])
    tab_width = font.measure(' ' * 4)
    widget.config(tabs=(tab_width,))

class StorageManager:
    def __init__(self, widget, path):
        assert isinstance(widget, tk.Text)
        self.widget = widget
        self.path = path

        if self.path in os.listdir():
            self.load()
        else:
            with open(self.path, 'w') as f:
                f.write('')

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

class EmbeddingsWindow(tk.Toplevel):
    """Widget with embedding search functionality.
    Uses embeddings_module.DataHandler class

    Functions related to embedding search:
        - get_search_term()
        - get_search_params()
        - embsearch()
    """
    def __init__(self, data_handler, scratchpads_object, config_handler, window_settings, input_editor_settings, output_editor_settings):
        self.scratchpads_object = scratchpads_object
        self.data_handler = data_handler

        super().__init__()
        self.nb = ttk.Notebook(self)
        self.editor = tk.Text(self.nb)
        self.outputs_editor = tk.Text(self.nb)
        self.scratchpads_object.connect_other_widget(self)

        # for saving and loading on ctrl+s and ctrl+l
        self.storage_manager = StorageManager(self.editor, 'embsearch_input.txt')
        self.storage_manager = StorageManager(self.outputs_editor, 'embsearch_output.txt')

        config_handler.apply_config(self, window_settings)
        config_handler.apply_config(self.editor, input_editor_settings)
        config_handler.apply_config(self.outputs_editor, output_editor_settings)
        set_tab_length(self.editor, 4)
        set_tab_length(self.outputs_editor, 4)

        self.nb.pack()
        self.nb.add(self.editor, text='inputs')
        self.nb.add(self.outputs_editor, text='outputs')

        self.bind('<KeyPress>', self.on_keypress, add='+')

    def on_keypress(self, event):
        if event.keysym == 'e' and event.state == 12:
            self.embsearch()

    def get_search_params(self):
        content = self.editor.get(1.0, 'end')[:-1]
        string = get_flagged(content, 'search params')
        search_params = json.loads(string)

        defaults = {
            'n': 3,
            'hasno': ['search terms', 'search term'],
            'has': [],
        }
        for k,v in defaults.items():
            if k not in search_params:
                search_params[k] = v
        search_params['n'] = int(search_params['n'])

        return search_params

    def get_search_term(self):
        content = self.editor.get(1.0, 'end')[:-1]
        content = self.scratchpads_object.apply_replacements(content)
        searchterm = get_flagged(content, 'search term')  # finds text between [flag] and [/flag]
        return searchterm

    def embsearch(self):
        # just wrap everything in to_call for multithreading
        def to_call():
            print('embsearch called')
            def res_to_string(res):
                lines = []
                for item in res:
                    for k,v in item.items():
                        lines.append(f'{k}:\n{v}')
                    lines.append('-'*10)
                return '\n'.join(lines)

            searchterm = self.get_search_term()
            search_params = self.get_search_params()
            res = self.data_handler.search(
                self.data_handler.get_embedding(searchterm),
                search_params,
            )

            self.outputs_editor.delete(1.0, 'end')
            self.outputs_editor.insert('end', '\n'.join([
                'search term:',
                '='*10,
                searchterm,
                '='*10,
                '',
                '',
            ]))
            self.outputs_editor.insert('end', res_to_string(res))
            self.nb.select(1)  # select outputs tab

        new_thread(to_call)
    
    def embsearch_custom(self, searchterm, search_params):
        # wrap everything in to_call for multithreading
        def to_call():
            def res_to_string(res):
                lines = []
                for item in res:
                    for k,v in item.items():
                        lines.append(f'{k}:\n{v}')
                    lines.append('-'*10)
                return '\n'.join(lines)

            res = self.data_handler.search(
                self.data_handler.get_embedding(searchterm),
                search_params,
            )

            self.outputs_editor.delete(1.0, 'end')
            self.outputs_editor.insert('end', '\n'.join([
                'search term:',
                '='*10,
                searchterm,
                '='*10,
                ''
            ]))
            self.outputs_editor.insert('end', res_to_string(res))
            self.nb.select(1)

        new_thread(to_call)

class ChatgptPrompter(tk.Toplevel):
    """Widget with chatgpt functionality. Uses chatgpt_stuff.py

    Converts between a list of dictionaries (messages) and pretty text with:
        - text_to_messages(text)
        - messages_to_text(messages)

    Prompts ChatGPT with:
        - generate()
    """

    def __init__(self, scratchpads, config_handler, settings):
        self.scratchpads = scratchpads

        super().__init__()
        self.editor = tk.Text(self)
        self.editor.pack()
        config_handler.apply_config(self, settings)
        config_handler.apply_config(self.editor, settings)
        set_tab_length(self.editor, 4)

        # for saving and loading on ctrl+s and ctrl+l
        self.storage_manager = StorageManager(self.editor, 'chatgpt_prompter.txt')
        
        self.scratchpads.connect_other_widget(self)

        self.bind('<KeyPress>', self.on_keypress, add='+')

    def text_to_messages(self, text):
        lines = text.split('\n')
        blocks = []
        current_block = []
        for line in lines:
            if line == '-----':
                blocks.append(current_block)
                current_block = []
            else:
                current_block.append(line)
        if current_block != []:
            blocks.append(current_block)
        messages = []
        for block in blocks:
            messages.append({
                'role': block[0],
                'content': '\n'.join(block[1:]),
            })
        return messages
    
    def messages_to_text(self, messages):
        blocks = []
        for item in messages:
            blocks.append(item['role'] + '\n' + item['content'])
        return '\n-----\n'.join(blocks)

    def add_message(self, role, content):
        text = self.editor.get(1.0, 'end')[:-1]
        messages = self.text_to_messages(text)
        messages.append({
            'role': role,
            'content': content,
        })
        new_text = self.messages_to_text(messages)
        self.editor.delete(1.0, 'end')
        self.editor.insert('1.0', new_text)
        self.editor.see('end')
    
    def remove_message(self):
        text = self.editor.get(1.0, 'end')[:-1]
        messages = self.text_to_messages(text)
        messages.pop()
        new_text = self.messages_to_text(messages)
        self.editor.delete(1.0, 'end')
        self.editor.insert('1.0', new_text)
        self.editor.see('end')

    def generate(self):
        # just wrap everything in to_call for multithreading
        def to_call():
            print('chatgpt called')
            response = chatgpt_stuff.use_chatgpt(  # lisp style  :p
                self.text_to_messages(
                    self.scratchpads.apply_replacements(
                        self.editor.get(1.0, 'end')[:-1]
                    )
                )
            )
            self.add_message('assistant', response)

            autoembed = get_flagged(emb_window.editor.get(1.0, 'end')[:-1], 'autoembed')
            if autoembed == 'true':
                emb_window.embsearch_custom(response, emb_window.get_search_params())

        new_thread(to_call)

    def on_keypress(self, event):
        if event.keysym == 'g' and event.state == 12:
            self.generate()
        elif event.keysym == '1' and event.state == 12:
            self.add_message('system', '')
        elif event.keysym == '2' and event.state == 12:
            self.add_message('user', '')
        elif event.keysym == '3' and event.state == 12:
            self.add_message('assistant', '')
        elif event.keysym == 'r' and event.state == 12:
            self.remove_message()

def get_selected(text_widget):
    # returns mouse-selected text from a tk.Text widget
    try:
        text_widget.selection_get()
    except:
        return None
    else:
        return text_widget.selection_get()

class TextWithListbox(tk.Frame):
    def __init__(self, parent, config_handler, editor_settings, listbox_settings):
        # create
        super().__init__(parent)
        self.config(background='black')
        self.pack()
        self.listbox = tk.Listbox(self)
        self.editor = tk.Text(self)
        config_handler.apply_config(self.listbox, listbox_settings)
        config_handler.apply_config(self.editor, editor_settings)
        set_tab_length(self.editor, 4)

        # for saving and loading on ctrl+s and ctrl+l
        self.storage_manager = StorageManager(self.editor, 'main.txt')

        # place
        padding = (5, 0)
        self.listbox.grid(row=0, column=0, padx=padding[0], pady=padding[1])
        self.editor.grid(row=0, column=1, padx=padding[0], pady=padding[1])

        # rest
        self.storage_manager.load()

        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        self.listbox.bind('<KeyPress>', self.listbox_on_keypress)
        parent.bind('<KeyPress>', self.on_keypress, add='+')

    def update_listbox(self):
        """Will put all lines that start with '#' into the listbox"""

        self.header_info = {}

        content = self.editor.get("1.0", "end")[:-1]
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#'):
                self.header_info[line] = i+1
        self.listbox.delete(0, 'end')
        for header in self.header_info.keys():
            self.listbox.insert('end', header)

    def on_listbox_select(self, event):
        # scroll to the header and highlight it
        sel = self.listbox.curselection()
        if sel == ():
            pass
        else:
            text_box = self.editor
            header_highlights = {
                'foreground':'yellow',
            }
            # get line
            index = int(sel[0])
            lb_item = self.listbox.get(index)
            line_number = self.header_info[lb_item]
            # highlight
            text_box.tag_remove('header_highlight', '1.0', 'end')
            text_box.tag_add('header_highlight', f'{line_number}.0', f'{line_number}.0 lineend')
            text_box.tag_config('header_highlight', **header_highlights)
            # go there
            text_box.mark_set('insert', f'{line_number}.0')
            text_box.see(f'{line_number}.0')

    def listbox_on_keypress(self, event):
        # go to selected header on enter
        if event.keysym == 'Return':
            self.editor.focus()

    def on_keypress(self, event):
        # enable navigation with alt+arrow
        if event.keysym == 'Left' and event.state == 393224:
            self.listbox.focus_set()
        elif event.keysym == 'Right' and event.state == 393224:
            self.editor.focus_set()

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
            'insertbackground': '{color 2}',
            'selectbackground': '{color 2}',
            'selectforeground': '{color 1}',
            'font': '{default font}',
            'width': 10,
            'height': 20,
        },
    }
    def __init__(self, config_path):
        self.config_path = config_path

        # this is only needed the first time
        if 'default_config.json' not in os.listdir():
            with open('default_config.json', 'w') as f:
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

def extra_replacements(string):
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

def main():
    global main_frame, scratchpads_window, chatgpt_prompter, emb_window

    """
    Creates 4 windows:
        - root -- main window for just writing. puts all lines that start with '#' into a listbox, which you can click to navigate to it.

        - chatgpt_window -- chatgpt prompter, under the hood it goes back and forth between a `messages` list of dictionaries and nicer-looking text, and can use chatgpt_stuff.py to make API calls with the `messages` list.

        - emb_window -- uses embeddings_module.DataHandler for doing text-similarity search. has one tab for the search query and settings, and another for displaying the search results.

        - scratchpads_window -- has tabs you can open by hitting F1-F9 from any other window, and you can access text within the tabs by writing `F{number}`. for example, "how to do {F2} in python", in the chatgpt prompter.
    """

    data_handler = embeddings_module.DataHandler()  # uses OpenAI endpoint for embeddings stuff
    def embed_contents(event):
        if isinstance(event.widget, tk.Text):
            if event.keysym == 'q' and event.state == 12:
                # not multithreading this because it might go wrong when multiple threads try to edit the same files

                print(col('re', 'started embedding strings, app will freeze until its done'))

                contents = event.widget.get(1.0, 'end')[:-1]
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
                    data_handler.get_embedding(  # will retrieve the embedding and add it to the database
                        '\n'.join(lines),
                        tags,
                    )

                print(col('gr', 'done embedding strings'))

    config_handler = ConfigHandler('config.json')
    config_handler.reset_default()
    config = config_handler.get_config()

    root_settings = config_handler.apply_meta(config['main'], config['meta'])
    chatgpt_settings = config_handler.apply_meta(config['chatgpt'], config['meta'])
    emb_settings = config_handler.apply_meta(config['embeddings'], config['meta'])
    scratchpads_settings = config_handler.apply_meta(config['scratchpads'], config['meta'])
    lb_settings = config_handler.apply_meta(config['listbox'], config['meta'])

    # config done, creating widgets

    ## main window
    root = tk.Tk()
    config_handler.apply_config(root, root_settings)
    ## scratchpads window
    scratchpads_window = tk.Toplevel()
    config_handler.apply_config(scratchpads_window, scratchpads_settings)
    scratchpads = Scratchpads(
        scratchpads_window,
        'scratchpads.json',
        editor_settings={k:v for k,v in scratchpads_settings.items() if k not in ['geometry', 'title']},
    )
    scratchpads.add_replacer(extra_replacements)
    ### order jankiness
    main_frame = TextWithListbox(
        root,
        config_handler,
        root_settings,
        lb_settings,
    )
    scratchpads.connect_other_widget(root)
    config_handler.apply_config(root, root_settings)
    ## chatgpt window
    chatgpt_prompter = ChatgptPrompter(
        scratchpads,
        config_handler,
        chatgpt_settings,
    )
    ## embeddings window
    emb_window = EmbeddingsWindow(
        data_handler,
        scratchpads,
        config_handler,
        emb_settings,
        emb_settings,
        emb_settings,
    )

    # focus
    main_frame.editor.focus_set()
    main_frame.editor.see(1.0)
    main_frame.editor.mark_set('insert', 1.0)

    def focus_all():
        widgets = [root, scratchpads_window, chatgpt_prompter, emb_window]
        for w in widgets:
            w.focus_set()
        root.focus_set()
        main_frame.editor.focus_set()

    root.bind_all('<Escape>', lambda event:focus_all())
    root.bind_all('<KeyPress>', embed_contents, add='+')

    root.mainloop()

main()
