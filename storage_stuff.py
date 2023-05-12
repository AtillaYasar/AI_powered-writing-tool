"""
- Cache:
    for storing input and output data, meant for API calls and downloads that take a long time.
- PersistenceABC:
    for saving and loading data in arbitrary objects.
    
Usage notes (personal experience):
    - PersistenceABC docs not clear enough; i had to figure out how to use it.
"""

import json, os
from abc import ABC, abstractmethod

def open_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def make_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# I wish this supported storage of nested objects
class PersistenceABC(ABC):
    """Handles saving to and loading from a file

    Note from myself to myself after using this:
    --
    on init -- need to call super().__init__(path)

    Arguments:
    --
    path -- the file where a description of your object is stored (for implement_filedata)

    Abstract methods:
    --
    object_to_filedata() -- Should return something that you can put into a file. (for saving)
    implement_filedata(filedata) -- Use data (like a dict or string or list) to edit/create/etc, the object. (for loading)

    Will grant you these methods:
    --
    save() -- Store the current state of the object in self.path
    load() -- Get data from self.path and implement it

    Dependencies
    --
    text_create(path, content)
    text_read(path)
    make_json(dic_or_list, path)
    open_json(path)
    """

    def __init__(self, path):
        """Set path, saver and loader"""

        self.path = path
        self.ext = path.split('.')[-1]
        
        # set saver and loader
        if self.ext == 'txt':
            self._saver = self._save_txt
            self._loader = self._load_txt
        elif self.ext == 'json':
            self._saver = self._save_json
            self._loader = self._load_json
        else:
            raise ValueError(f'extension must be txt or json, but path is {path}')

    # Set these to be allowed to use this class.

    @abstractmethod
    def object_to_filedata(self):
        """Should return something that you can put into a file. (for saving)"""
        pass
    @abstractmethod
    def implement_filedata(self, filedata):
        """Use data (like a dict or string or list) to edit/create/etc, the object. (for loading)"""
        pass

    # internal methods

    ## save to self.path
    def _save_txt(self, contents):
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(contents)
    def _save_json(self, contents):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(contents, f, indent=2)

    ## load from self.path
    def _load_txt(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            contents = f.read()
        return contents
    def _load_json(self):
        with open(self.path, 'r', encoding="utf-8") as f:
            contents = json.load(f)
        return contents

    # external methods

    def save(self):
        """Store the current state of the object in self.path"""
        filedata = self.object_to_filedata()
        self._saver(filedata)

    def load(self):
        """Get data from self.path and implement it"""
        filedata = self._loader()
        self.implement_filedata(filedata)


class Cache:
    # intended for storing API calls and downloads that take a long time

    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump([], f)
        self.cache = self.load_cache()

    def load_cache(self):
        cache = open_json(self.filename)
        return cache

    def save_cache(self):
        make_json(self.cache, self.filename)
        print(f'saved to {self.filename}')

    def get(self, inp):
        for item in self.cache:
            if item['input'] == inp:
                return item['output']
        return None

    def add(self, inp, outp):
        self.cache.append({'input':inp, 'output':outp})
        self.save_cache()
    
    def edit(self, inp, outp):
        "returns True if edited, False if not"

        for n, item in enumerate(self.cache):
            if item['input'] == inp:
                self.cache[n]['output'] = outp
                self.save_cache()
                return True
        return False

    def investigate(self, terms):
        "returns a list of items that contain the terms"

        allowed_keys = ['simple_match', 'multi_match', 'by_funcion']
        if not all([key in allowed_keys for key in terms.keys()]):
            print(f'invalid key, allowed keys are {allowed_keys}')
            return None

        results = []
        simple_match = terms.get('simple_match', None)
        multi_match = terms.get('multi_match', None)
        by_funcion = terms.get('by_funcion', None)
        for item in self.cache:
            if simple_match != None:
                if simple_match in str(item):
                    results.append(item)
                    continue
            if multi_match != None:
                if all([term in str(item) for term in multi_match]):
                    results.append(item)
                    continue
            if by_funcion != None:
                if by_funcion(item):
                    results.append(item)
                    continue
        
        return results

    def delete(self, inp):
        "returns True if deleted, False if not"

        for n, item in enumerate(self.cache):
            if item['input'] == inp:
                del self.cache[n]
                self.save_cache()
                return True
        return False

