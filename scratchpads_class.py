import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import json, os, time

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
class Scratchpads:
    '''
    external methods:
        - get(key) <-- key is F1-F9
        - get_all() <-- returns dict of all contents
        - save_to(path optional) <-- saves content dict as json
        - load_from(path optional) <-- loads from json
        - connect_other_widget(widget) <-- lets you press F1-F9 in other widget to switch to tab
    '''
    def __init__(self, parent, path, editor_settings=None, entry_box_settings=None):
        self.w = parent
        self.path = path

        self.opened = False
        self.f_to_content = {}
        self.f_to_widget = {}

        self.extra_replacers = []

        if editor_settings == None:
            self.editor_settings = {
                'width': 50,
                'height': 25,
                'font': ("comic sans", 14),
                'bg': 'black',
                'fg': 'white',
                'insertbackground': 'white',
                'selectbackground': 'white',
                'selectforeground': 'black',
            }
        else:
            self.editor_settings = editor_settings
        if entry_box_settings == None:
            self.entry_box_settings = {
                'bg': 'black',
                'fg': 'white',
                'insertbackground': 'white',
                'selectbackground': 'white',
                'selectforeground': 'black',
                'font': ('comic sans', 14),
            }
        else:
            self.entry_box_settings = entry_box_settings

        # some default content
        for n in range(9):
            key = f'F{str(n+1)}'
            self.f_to_content[key] = f'hi i am tab {key}'

        load_attempt = self.load()
        if load_attempt == False:
            self._warning('load attempt failed')

        self._open()
        self._to_tab('F9')

        self.w.bind('<KeyPress>', self._on_press, add='+')
        self.w.bind('<KeyPress>', self.fkey_bindings, add='+')
        self.entry_box.bind('<Return>', self.entry_command)
    
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
    
    def change_fontsize(self, new):
        self.editor_settings['font'] = new
        for f, widget in self.f_to_widget.items():
            widget.config(font=new)
        
    def _parse_command(self, cmd):
        if cmd == 'font up':
            cur = self.editor_settings['font'][1]
            new = (self.editor_settings['font'][0], cur+1)
            self.change_fontsize(new)
        elif cmd == 'font down':
            cur = self.editor_settings['font'][1]
            new = (self.editor_settings['font'][0], cur-1)
            self.change_fontsize(new)
    
    def entry_command(self, event):
        cmd = self.entry_box.get()
        self._parse_command(cmd)

    def _open(self):
        self.w.title('scratchpads')
        self.w.config(background = 'black')
        self.nb = ttk.Notebook(self.w)

        for f, content in self.f_to_content.items():
            self._add_tab(f, content)

        self.nb.pack()
        self.opened = True

        self.entry_box = tk.Entry(
            self.w,
            **self.entry_box_settings,
        )
        self.entry_box.pack()

    def _to_tab(self, f):
        # select tab
        self.w.focus_set()
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
    
    def connect_other_widget(self, other_widget):
        other_widget.bind('<KeyPress>', self.fkey_bindings, add='+')

    def get(self, f):
        # returns the contents of the tab
        if f in f_to_widget:
            w = self.f_to_widget[f].get(1.0, 'end')[:-1]
            return w
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
            if self.opened:
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