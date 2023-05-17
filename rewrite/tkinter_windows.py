import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import json, os, time, threading

# chatgpt and openai
import chatgpt_stuff

from overall_imports import open_json, make_json

# executes a given function on a new thread, so that the app doesn't freeze while it is running
def new_thread(function):
    threading.Thread(target=function).start()

def get_flagged(string, flag):
    if f'[{flag}]' in string and f'[/{flag}]' in string:
        flagged = string.partition(f'[{flag}]')[2].partition(f'[/{flag}]')[0][1:-1]
        return flagged
    else:
        return None

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

# set of text editors, accessible by F1-F9
class Scratchpads(tk.Toplevel):
    '''
    external methods:
        - get(key) <-- key is F1-F9
        - get_all() <-- returns dict of all contents
        - save_to(path optional) <-- saves content dict as json
        - load_from(path optional) <-- loads from json
        - connect_other_widget(widget) <-- lets you press F1-F9 in other widget to switch to tab
    '''
    def __init__(self, path, editor_settings, entry_box_settings):
        super().__init__()
        self.path = path

        self.f_to_content = {}
        self.f_to_widget = {}

        self.extra_replacers = []
        self.editor_settings = editor_settings
        self.entry_box_settings = entry_box_settings

        # get contents dictionary
        if os.path.exists(path):
            json_file = open_json(path)
            for f, content in json_file.items():
                self.f_to_content[f] = content
            print(f'loaded from file, {path}')
        else:
            # some default content
            for n in range(9):
                key = f'F{str(n+1)}'
                self.f_to_content[key] = f'hi i am tab {key}'
            print('loaded from default')

        # use contents dictionary to create tabs
        self._create()

        self._to_tab('F9')

        self.bind('<KeyPress>', self._on_press, add='+')
        self.bind('<KeyPress>', self.fkey_bindings, add='+')
        self.entry_box.bind('<Return>', self.entry_command)

    def _create(self):
        self.title('scratchpads')
        self.config(background = 'black')
        self.nb = ttk.Notebook(self)

        self.nb.pack()

        self.entry_box = tk.Entry(
            self,
            **self.entry_box_settings,
        )
        self.entry_box.pack()

        for f, content in self.f_to_content.items():
            self._add_tab(f, content)

    def _warning(self, msg):
        print(col('re', msg))

    def _add_tab(self, f, content):
        title = f'- {f} -'
        widget = tk.Text(self.nb, **self.editor_settings)
        set_tab_length(widget, 4)
        self.nb.add(widget, text=title)
        self.f_to_widget[f] = widget
        self.f_to_content[f] = content
        widget.insert(1.0, content)
        
    def _parse_command(self, cmd):
        # `split`
        def split_contents():
            # helper for text embeddings, splits the text into sections separated by a '=====' line
            current_f = self.get_focus()
            current_content = self.get(current_f)

            paragraphs = current_content.split('\n\n')
            new_content = '\n=====\n'.join(paragraphs)
            self.set(current_f, new_content)

        # `tag all`
        def tag_all(tag):
            # helper for text embeddings, adds a !!!{tag} line to the beginning of each section
            current_f = self.get_focus()
            current_content = self.get(current_f)

            sections = current_content.split('\n=====\n')
            for n, s in enumerate(sections):
                lines = s.split('\n')
                lines.insert(0, f'!!!{tag}')
                sections[n] = '\n'.join(lines)

            new_content = '\n=====\n'.join(sections)
            self.set(current_f, new_content)

        # `font up` and `font down`
        def change_fontsize(new):
            self.editor_settings['font'] = new
            for f, widget in self.f_to_widget.items():
                widget.config(font=new)

        if cmd == 'font up':
            cur = self.editor_settings['font'][1]
            new = (self.editor_settings['font'][0], cur+1)
            self.change_fontsize(new)
        elif cmd == 'font down':
            cur = self.editor_settings['font'][1]
            new = (self.editor_settings['font'][0], cur-1)
            self.change_fontsize(new)
        elif cmd == 'split':
            split_contents()
        elif cmd.startswith('tag all'):
            tag = cmd.partition('tag all ')[2]
            tag_all(tag)
    
    def entry_command(self, event):
        cmd = self.entry_box.get()
        self._parse_command(cmd)

    def _to_tab(self, f):
        # select tab
        self.focus_set()
        widget = self.f_to_widget[f]
        t = self.nb.tabs()
        idx = t.index(str(widget))
        self.nb.select(idx)

        to_index = '1.0'
        # focus
        widget.focus_set()
        widget.mark_set('insert', to_index)
        # scroll to end
        widget.see(to_index)

    def _on_press(self, event):
        '''
        ctrl+s: save
        ctrl+b: backup
        ctrl+l: load
        '''
        keysym = event.keysym
        state = event.state

        if keysym == 's' and state == 12:
            self.save()
        elif keysym == 'b' and state == 12:
            self.backup()
        elif keysym == 'l' and state == 12:
            self.load()
    
    def fkey_bindings(self, event):
        """f1-f9: switch to tab"""

        keysym = event.keysym
        if keysym == 'F4' and event.state == 131080:
            #self.backup()
            exit()
        if keysym in [f'F{i}' for i in range(1, 10)]:
            self._to_tab(keysym)

    def get(self, f):
        # returns the contents of the tab
        if f in self.f_to_widget:
            content = self.f_to_widget[f].get(1.0, 'end')[:-1]
            return content
        else:
            self._warning(f'{f} not in f_to_widget')
            return None
    
    def get_all(self):
        contents = {}
        for f, widget in self.f_to_widget.items():
            contents[f] = widget.get(1.0, 'end')[:-1]
        return contents
    
    def get_focus(self):
        # returns the key for the selected tab
        selected = self.nb.select()
        inverted = {str(w):f for f,w in self.f_to_widget.items()}
        f = inverted[selected]
        return f

    def set(self, f, content):
        if f not in [f'F{n}' for n in range(1, 10)]:
            self._warning(f'{f} not in [F1-F9]')
            return
        if f not in self.f_to_content:
            self._warning(f'{f} not in f_to_content')
        else:
            self.f_to_content[f] = content
            self.f_to_widget[f].delete(1.0, 'end')
            self.f_to_widget[f].insert(1.0, content)

    def save(self, path=None):
        if path == None:
            path = self.path
        for f, widget in self.f_to_widget.items():
            self.f_to_content[f] = widget.get(1.0, 'end')[:-1]
        with open(path, 'w') as f:
            json.dump(self.f_to_content, f, indent=4)
        print(col('gr', f'saved to {path}'))

    def backup(self):
        backups_folder = 'scratchpads_backups'
        if not os.path.exists(backups_folder):
            os.mkdir(backups_folder)
        name = f'scratchpads_{time.time()}.json'
        path = os.path.join(backups_folder, name)
        self.save(path)

    def load(self, path=None):
        if path == None:
            path = self.path
        if not os.path.exists(path):
            self._warning(f'file {path} not found')
            return False
        else:
            with open(path, 'r') as f:
                loaded = json.load(f)
            for f, content in loaded.items():
                self.set(f, content)
            print(col('gr', f'loaded from {path}'))
            return True
    
    def write_to(self, f, content, tag=None):
        widget = self.f_to_widget[f]
        widget.insert('end', content, tag)
        #widget.see('end')

    def apply_replacements(self, string):
        per_tab = self.get_all()
        for f, content in per_tab.items():
            to_replace = '{' + f.lower() + '}'
            if to_replace in string:
                string = string.replace(to_replace, content)

        # hacky addon
        for func in self.extra_replacers:
            string = func(string)

        return string
    
    def add_replacer(self, func):
        self.extra_replacers.append(func)

    def goto(self):
        w = self
        w.state(newstate='normal')
        w.focus_set()

        tab = self.get_focus()
        self.f_to_widget[tab].focus_set()


class EmbeddingsWindow(tk.Toplevel):
    """Widget with embedding search functionality.
    Uses embeddings_module.DataHandler class

    Functions related to embedding search:
        - get_search_term()
        - get_search_params()
        - embsearch()
    """
    def __init__(self, data_handler):
        self.data_handler = data_handler

        super().__init__()
        self.nb = ttk.Notebook(self)
        self.inputs_editor = tk.Text(self.nb)
        self.outputs_editor = tk.Text(self.nb)

        self.nb.pack()
        self.nb.add(self.inputs_editor, text='inputs')
        self.nb.add(self.outputs_editor, text='outputs')

    def get_search_params(self):
        content = self.inputs_editor.get(1.0, 'end')[:-1]
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
        content = self.inputs_editor.get(1.0, 'end')[:-1]
        content = self.scratchpads.apply_replacements(content)
        searchterm = get_flagged(content, 'search term')  # finds text between [flag] and [/flag]
        return searchterm

    def embsearch(self, searchterm, search_params):
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
            # helper function
            def res_to_string(res):
                lines = []
                for item in res:
                    for k,v in item.items():
                        lines.append(f'{k}:\n{v}')
                    lines.append('-'*10)
                return '\n'.join(lines)

            # embed search term and do search
            res = self.data_handler.search(
                self.data_handler.get_embedding(searchterm),
                search_params,
            )

            # display results
            self.outputs_editor.delete(1.0, 'end')
            self.outputs_editor.insert('end', '\n'.join([
                'search term:',
                '='*10,
                searchterm,
                '='*10,
                '',
                res_to_string(res),
            ]))

            # open outputs tab
            self.nb.select(1)

        new_thread(to_call)

    def goto(self):
        w = self
        w.state(newstate='normal')
        w.focus_set()
        self.outputs_editor.focus_set()
        self.nb.select(1)


class ChatgptPrompter(tk.Toplevel):
    """Widget with chatgpt functionality. Uses chatgpt_stuff.py

    Converts between a list of dictionaries (messages) and pretty text with:
        - text_to_messages(text)
        - messages_to_text(messages)

    Prompts ChatGPT with:
        - generate()
    """

    def __init__(self):
        super().__init__()
        self.title('chatgpt prompter')
        self.editor = tk.Text(self)
        self.editor.pack()

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

            emb_window = self.emb_window
            autoembed = get_flagged(emb_window.inputs_editor.get(1.0, 'end')[:-1], 'autoembed')
            #autoembed = 'true'
            if autoembed == 'true':
                emb_window.embsearch_custom(response, emb_window.get_search_params())
            
            self.state(newstate='normal')
            self.editor.focus_set()


        new_thread(to_call)

    def goto(self):
        w = self
        w.state(newstate='normal')
        w.focus_set()
        self.editor.focus_set()



class TextWithListbox(tk.Frame):
    def __init__(self, parent):
        # create
        super().__init__(parent)
        self.pack()

        self.parent = parent

        self.config(background='black')
        self.listbox = tk.Listbox(self)
        self.editor = tk.Text(self)

        # place
        padding = (5, 0)
        self.listbox.grid(row=0, column=0, padx=padding[0], pady=padding[1])
        self.editor.grid(row=0, column=1, padx=padding[0], pady=padding[1])

        self.listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        self.listbox.bind('<KeyPress>', self.listbox_on_keypress)
        parent.bind('<KeyPress>', self.on_keypress)

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
    
    def goto(self):
        w = self.parent
        w.state(newstate='normal')
        self.editor.focus_set()

