# AI_powered-writing-tool
Tkinter app that uses OpenAI's ChatGPT (3.5) and embeddings endpoint to help with writing text.

## how to use
- download  (for example with `gh repo clone AtillaYasar/AI_powered-writing-tool`, or by downloading the zip and unzipping)
- run main.py  (double click)
- read stuff in f9 tab in the `scratchpads` window, on the top right for general explanation  (which is repeated below)
- to use OAI api (for chatgpt and embeddings-search), put api key in `secret_things.py`

## general explanation  (also in app, in f9 tab)
```
main features:
	- chatgpt prompter
	- text-similarity search, with ability to filter by metadata tags  (using OAI's embeddings endpoint)
		+ can update embeddings database from within app
	- can access other windows' text by writing {placeholder} before API calls
		+ for example in the chatgpt prompter, "hey how do i do {f3} in python, in my program? here is my code: {main}". this will put text from the f3 tab, and from the "main editor", into the prompt, then call chatgpt.
	- customizable layout  (from config.json)
	- save text with ctrl+s


hotkeys

# global
Escape -- bring all windows to the front
ctrl+s -- save text in current editor
ctrl+l -- load text from textfile into current editor
F1-F9 -- open tab in scratchpads window (top left by default)
ctrl+q -- add the contents of the widget to the embeddings database
	- you can store multiple embeddings at once, by splitting them by a ===== line
	- lines starting with !!! will be used as metadata tags
(alt+f4 closes everything, unlike the default tkinter behavior)

# embedding window  (bottom left by default)
ctrl+e -- do similarity search

# chatgpt window  (bottom right by default)
ctrl+g -- use api on current conversation
ctrl+1 -- add "system" message
ctrl+2 -- add "user" message
ctrl+3 -- add "assistant" message
ctrl+r -- remove last message

# placeholder values
if you write {placeholder} anywhere, it will replace it with the text that is referred, for any API calls
is case-insensitive
## available values:
	- f1 to f9: scratchpad tab contents.
		example: {f1}
	- main: main editor contents  (top left)
	- chatgpt.full: chatgpt conversation
	- chatgpt.latest: last message in chatgpt conversation
	- chatgpt.last: same as above.
```


## note
app is in development  
