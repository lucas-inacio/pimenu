import os
import subprocess
import sys
import threading
from tkinter import Tk, Frame, Button, PhotoImage, Text, constants as TkC, INSERT, messagebox
from math import sqrt, floor, ceil
from queue import Queue, Empty

from yaml import Loader
import yaml

import argparse
import re

def enqueue_ouput(out, q):
    for line in iter(out.readline, ''):
        if not line:
            break
        q.put(line)
    out.close()

def run_sub(args):
    p = subprocess.Popen(args, stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) # line buffered
    q = Queue()
    t = threading.Thread(target=enqueue_ouput, args=(p.stdout, q))
    t.daemon = True
    t.start()
    return p, q

class FlatButton(Button):
    def __init__(self, master=None, cnf=None, **kw):
        Button.__init__(self, master, cnf, **kw)

        self.config(
            compound=TkC.TOP,
            relief=TkC.FLAT,
            bd=0,
            bg="#b91d47",  # dark-red
            fg="white",
            activebackground="#b91d47",  # dark-red
            activeforeground="white",
            highlightthickness=0
        )

    def set_color(self, color):
        self.configure(
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white"
        )


class PiMenu(Frame):
    framestack = []
    icons = {}
    path = ''
    lastinit = 0

    def __init__(self, parent):
        Frame.__init__(self, parent, background="white")
        self.parent = parent
        self.pack(fill=TkC.BOTH, expand=1)

        self.path = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.initialize()

    def initialize(self):
        """
        (re)load the the items from the yaml configuration and (re)init
        the whole menu system

        :return: None
        """
        with open(self.path + '/pimenu.yaml', 'r') as f:
            doc = yaml.load(f, Loader=Loader)
        self.lastinit = os.path.getmtime(self.path + '/pimenu.yaml')

        if len(self.framestack):
            self.destroy_all()
            self.destroy_top()

        self.show_items(doc)

    def has_config_changed(self):
        """
        Checks if the configuration has been changed since last loading

        :return: Boolean
        """
        return self.lastinit != os.path.getmtime(self.path + '/pimenu.yaml')

    def show_items(self, items, upper=None):
        """
        Creates a new page on the stack, automatically adds a back button when there are
        pages on the stack already

        :param items: list the items to display
        :param upper: list previous levels' ids
        :return: None
        """
        if upper is None:
            upper = []
        num = 0

        # create a new frame
        wrap = Frame(self, bg="black")

        if len(self.framestack):
            # when there were previous frames, hide the top one and add a back button for the new one
            self.hide_top()
            back = FlatButton(
                wrap,
                text='back…',
                image=self.get_icon("arrow.left"),
                command=self.go_back,
            )
            back.set_color("#00a300")  # green
            back.grid(row=0, column=0, padx=1, pady=1, sticky=TkC.W + TkC.E + TkC.N + TkC.S)
            num += 1

        # add the new frame to the stack and display it
        self.framestack.append(wrap)
        self.show_top()

        # calculate tile distribution
        allitems = len(items) + num
        rows = floor(sqrt(allitems))
        cols = ceil(allitems / rows)

        # make cells autoscale
        for x in range(int(cols)):
            wrap.columnconfigure(x, weight=1)
        for y in range(int(rows)):
            wrap.rowconfigure(y, weight=1)

        # display all given buttons
        for item in items:
            act = upper + [item['name']]

            if 'icon' in item:
                image = self.get_icon(item['icon'])
            else:
                image = self.get_icon('scrabble.' + item['label'][0:1].lower())

            btn = FlatButton(
                wrap,
                text=item['label'],
                image=image
            )

            if 'items' in item:
                # this is a deeper level
                btn.configure(command=lambda act=act, item=item: self.show_items(item['items'], act),
                              text=item['label'] + '…')
                btn.set_color("#2b5797")  # dark-blue
            else:
                # this is an action
                if 'command' in item:
                    # Handle paths with spaces
                    command = item['command'].split()
                    if command.count('"') % 2 != 0:
                        raise ValueError('Invalid pimenu.yaml')
                    final_args = []
                    for arg in item['command'].split():
                        if arg[-1] == '"':
                            final_args[-1] = final_args[-1] + ' ' + arg.replace('"', '')
                        else:
                            final_args.append(arg.replace('"', ''))

                    btn.configure(command=lambda args=final_args: self.go_action(args))

            if 'color' in item:
                btn.set_color(item['color'])

            # add buton to the grid
            btn.grid(
                row=int(floor(num / cols)),
                column=int(num % cols),
                padx=1,
                pady=1,
                sticky=TkC.W + TkC.E + TkC.N + TkC.S
            )
            num += 1

    def get_icon(self, name):
        """
        Loads the given icon and keeps a reference

        :param name: string
        :return:
        """
        if name in self.icons:
            return self.icons[name]

        ico = self.path + '/ico/' + name + '.png'
        if not os.path.isfile(ico):
            ico = self.path + '/ico/' + name + '.gif'
            if not os.path.isfile(ico):
                ico = self.path + '/ico/cancel.gif'

        self.icons[name] = PhotoImage(file=ico)
        return self.icons[name]

    def hide_top(self):
        """
        hide the top page
        :return:
        """
        self.framestack[len(self.framestack) - 1].pack_forget()

    def show_top(self):
        """
        show the top page
        :return:
        """
        self.framestack[len(self.framestack) - 1].pack(fill=TkC.BOTH, expand=1)

    def destroy_top(self):
        """
        destroy the top page
        :return:
        """
        self.framestack[len(self.framestack) - 1].destroy()
        self.framestack.pop()

    def destroy_all(self):
        """
        destroy all pages except the first aka. go back to start
        :return:
        """
        while len(self.framestack) > 1:
            self.destroy_top()

    def go_action(self, args):
        """
        execute the action script
        :param actions:
        :return:
        """
        # hide the menu and show a delay screen
        self.hide_top()
        delay = Frame(self, bg="#2d89ef")
        delay.pack(fill=TkC.BOTH, expand=1)
        delay.rowconfigure(0, weight=2)
        delay.rowconfigure(1, weight=1)
        delay.columnconfigure(0, weight=1)

        text = Text(delay, fg='white', bg='#2d89ef', font="Sans 10")
        text.bind('<Key>', lambda e: None) # Prevent editing
        text.grid(
            row=0,
            column=0,
            padx=1,
            pady=1,
            sticky=TkC.NS+TkC.EW
        )

        try:
            p, q = run_sub(args)
            button = FlatButton(delay, text='Encerrar', font='Sans 20', command=lambda : p.terminate())
            button.set_color('#333333')
            button.grid(
                row=1,
                column=0,
                padx=1,
                pady=1,
                sticky=TkC.NS+TkC.EW
            )
            self.parent.update()
            while p.poll() == None:
                try:
                    line = q.get_nowait()
                    text.insert(INSERT, line)
                    self.parent.update()
                except Empty:
                    pass
            messagebox.showinfo('Status', 'Processo encerrado')
        except OSError as e:
            messagebox.showerror(e)

        # remove delay screen and show menu again
        delay.destroy()
        self.destroy_all()
        self.show_top()

    def go_back(self):
        """
        destroy the current frame and reshow the one below, except when the config has changed
        then reinitialize everything
        :return:
        """
        if self.has_config_changed():
            self.initialize()
        else:
            self.destroy_top()
            self.show_top()


def main():
    root = Tk()
    root.geometry("480x320")
    root.wm_title('PiMenu')
    if len(sys.argv) > 1 and sys.argv[1] == 'fs':
        root.wm_attributes('-fullscreen', True)

    try:
        PiMenu(root)
        root.mainloop()
    except FileNotFoundError:
        messagebox.showerror('Error!', 'Missing pimenu.yaml')


if __name__ == '__main__':
    main()
    # # print(' '.join(sys.argv[1:]))
    # # print(sys.orig_argv)
    # # print(sys.argv)
    # parser = argparse.ArgumentParser('teste', 'usage', 'description')
    # parser.add_argument('str')
    # parser.add_argument('path')
    # # args = parser.parse_args(['teste', '"C:\\Users\\lucas\\OneDrive\\Python', 'Scripts\\show_dvr.py"'])

    # text = "python 'C:/Users/lucas/OneDrive/Python Scripts/show_dvr.py'"
    # items = []
    # for i in text:

    #     print(i)

    # # re.match('', ' '.join(sys.argv[1:]))
    # print(os.fsdecode(' '.join(sys.argv[1:])))
    # # print(args)
