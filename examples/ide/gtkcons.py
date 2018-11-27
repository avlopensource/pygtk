#!/usr/bin/env python

#   Interactive Python-GTK Console
#   Copyright (C),
#   1998 James Henstridge
#   2004 John Finlay
#
#    This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This module implements an interactive python session in a GTK window.  To
# start the session, use the gtk_console command.  Its specification is:
#   gtk_console(namespace, title, copyright)
# where namespace is a dictionary representing the namespace of the session,
#       title     is the title on the window and
#       copyright is any additional copyright info to print.
#
# As well as the starting attributes in namespace, the session will also
# have access to the list __history__, which is the command history.

import sys, string, traceback
import pygtk
pygtk.require('2.0')
import gobject
import gtk

stdout = sys.stdout

if not hasattr(sys, 'ps1'): sys.ps1 = '>>> '
if not hasattr(sys, 'ps2'): sys.ps2 = '... '

# some functions to help recognise breaks between commands
def remQuotStr(s):
    '''Returns s with any quoted strings removed (leaving quote marks)'''
    r = ''
    inq = 0
    qt = ''
    prev = '_'
    while len(s):
        s0, s = s[0], s[1:]
        if inq and (s0 != qt or prev == '\\'):
            prev = s0
            continue
        prev = s0
        if s0 in '\'"':
            if inq:
                inq = 0
            else:
                inq = 1
                qt = s0
        r = r + s0
    return r

def bracketsBalanced(s):
    '''Returns true iff the brackets in s are balanced'''
    s = [x for x in s if x in '()[]{}']
    stack = []
    brackets = {'(':')', '[':']', '{':'}'}
    while len(s) != 0:
        if s[0] in ")]}":
            if len(stack) != 0 and brackets[stack[-1]] == s[0]:
                del stack[-1]
            else:
                return 0
        else:
            stack.append(s[0])
        s = s[1:]
    return len(stack) == 0

class gtkoutfile:
    '''A fake output file object.  It sends output to a GTK TextView widget,
    and if asked for a file number, returns one set on instance creation'''
    def __init__(self, w, fn, font):
        self.__fn = fn
        self.__w = w
        self.__b = w.get_buffer()
        self.__ins = self.__b.get_mark('insert')
        self.__font = font
    def close(self): pass
    flush = close
    def fileno(self):    return self.__fn
    def isatty(self):    return 0
    def read(self, a):   return ''
    def readline(self):  return ''
    def readlines(self): return []
    def write(self, s):
        #stdout.write(str(self.__w.get_point()) + '\n')
        iter = self.__b.get_iter_at_mark(self.__ins)
        self.__b.insert_with_tags(iter, s, self.__font)
        self.__w.scroll_to_mark(self.__ins, 0.0)
        self.__w.queue_draw()
    def writelines(self, l):
        iter = self.__b.get_iter_at_mark(self.__ins)
        for s in l:
            self.__b.insert_with_tags(iter, s, self.__font)
        self.__w.scroll_to_mark(self.__ins, 0.0)
        self.__w.queue_draw()
    def seek(self, a):   raise IOError(29, 'Illegal seek')
    def tell(self):      raise IOError(29, 'Illegal seek')
    truncate = tell

class Console(gtk.VBox):
    def __init__(self, namespace={}, copyright='', quit_cb=None):
        gtk.VBox.__init__(self, spacing=2)
        self.set_border_width(2)
        self.copyright = copyright
        #self.set_size_request(475, 300)

        self.quit_cb = quit_cb

        self.inp = gtk.HBox()
        self.pack_start(self.inp)
        self.inp.show()

        self.scrolledwin = gtk.ScrolledWindow()
        self.scrolledwin.show()
        self.inp.pack_start(self.scrolledwin, padding=1)
        self.text = gtk.TextView()
        self.text.set_editable(False)
        self.text.set_wrap_mode(gtk.WRAP_WORD)
        self.text.set_size_request(500, 400)
        self.scrolledwin.add(self.text)
        self.text.show()
        self.buffer = self.text.get_buffer()
        #create the tags we will use
        self.normal = self.buffer.create_tag('Normal', font='Helvetica 10',
                                            foreground='black')
        self.title = self.buffer.create_tag('Title', font='Helvetica Bold 10',
                                            foreground='darkgreen')
        self.error = self.buffer.create_tag('Error', font='Helvetica 12',
                                           foreground='red')
        self.command = self.buffer.create_tag('Command',
                                             font='Helvetica Bold 10',
                                            foreground='blue')

        self.inputbox = gtk.HBox(spacing=2)
        self.pack_end(self.inputbox, expand=False)
        self.inputbox.show()

        self.prompt = gtk.Label(sys.ps1)
        self.prompt.set_padding(xpad=2, ypad=0)
        self.prompt.set_size_request(26, -1)
        self.inputbox.pack_start(self.prompt, fill=False, expand=False)
        self.prompt.show()

        self.closer = gtk.Button(stock=gtk.STOCK_CLOSE)
        self.closer.connect("clicked", self.quit)
        self.inputbox.pack_end(self.closer, fill=False, expand=False)
        self.closer.show()

        self.line = gtk.Entry()
        self.line.set_size_request(400,-1)
        self.line.connect("key_press_event", self.key_function)
        self.inputbox.pack_start(self.line, padding=2)
        self.line.show()

        # now let the text box be resized
        self.text.set_size_request(0, 0)
        self.line.set_size_request(0, -1)

        self.namespace = namespace

        self.cmd = ''
        self.cmd2 = ''

        # set up hooks for standard output.
        self.stdout = gtkoutfile(self.text, sys.stdout.fileno(),
                                self.normal)
        self.stderr = gtkoutfile(self.text, sys.stderr.fileno(),
                                self.error)

        # set up command history
        self.history = ['']
        self.histpos = 0
        self.namespace['__history__'] = self.history

    def init(self):
        self.text.realize()
        self.insert = self.buffer.get_mark('insert')
        iter = self.buffer.get_iter_at_mark(self.insert)
        self.buffer.insert_with_tags(iter, 'Python %s\n%s\n\n' %
                                     (sys.version, sys.copyright) +
                                     'Interactive Python-GTK Console - \n' +
                                     'Copyright (C)\n' \
                                     '1998 James Henstridge\n' \
                                     '2004 John Finlay\n\n' +
                                     self.copyright + '\n', self.title)
        self.text.scroll_to_mark(self.insert, 0.0)
        self.line.grab_focus()

    def quit(self, *args):
        self.hide()
        self.destroy()
        if self.quit_cb: self.quit_cb()

    def key_function(self, entry, event):
        if event.keyval == gtk.keysyms.Return:
            self.line.emit_stop_by_name("key_press_event")
            self.eval()
        if event.keyval == gtk.keysyms.Tab:
            self.line.emit_stop_by_name("key_press_event")
            self.line.append_text('\t')
            gobject.idle_add(self.focus_text)
        elif event.keyval in (gtk.keysyms.KP_Up, gtk.keysyms.Up):
            self.line.emit_stop_by_name("key_press_event")
            self.historyUp()
            gobject.idle_add(self.focus_text)
        elif event.keyval in (gtk.keysyms.KP_Down, gtk.keysyms.Down):
            self.line.emit_stop_by_name("key_press_event")
            self.historyDown()
            gobject.idle_add(self.focus_text)
        elif event.keyval in (gtk.keysyms.D, gtk.keysyms.d) and \
             event.state & gtk.gdk.CONTROL_MASK:
            self.line.emit_stop_by_name("key_press_event")
            self.ctrld()

    def focus_text(self):
        self.line.grab_focus()
        return False  # don't requeue this handler

    def ctrld(self):
        self.quit()

    def historyUp(self):
        if self.histpos > 0:
            l = self.line.get_text()
            if len(l) > 0 and l[0] == '\n': l = l[1:]
            if len(l) > 0 and l[-1] == '\n': l = l[:-1]
            self.history[self.histpos] = l
            self.histpos = self.histpos - 1
            self.line.set_text(self.history[self.histpos])

    def historyDown(self):
        if self.histpos < len(self.history) - 1:
            l = self.line.get_text()
            if len(l) > 0 and l[0] == '\n': l = l[1:]
            if len(l) > 0 and l[-1] == '\n': l = l[:-1]
            self.history[self.histpos] = l
            self.histpos = self.histpos + 1
            self.line.set_text(self.history[self.histpos])

    def eval(self):
        l = self.line.get_text() + '\n'
        if len(l) > 1 and l[0] == '\n': l = l[1:]
        self.histpos = len(self.history) - 1
        if len(l) > 0 and l[-1] == '\n':
            self.history[self.histpos] = l[:-1]
        else:
            self.history[self.histpos] = l
        self.line.set_text('')
        iter = self.buffer.get_iter_at_mark(self.insert)
        self.buffer.insert_with_tags(iter, self.prompt.get() + l, self.command)
        self.text.scroll_to_mark(self.insert, 0.0)
        if l == '\n':
            self.run(self.cmd)
            self.cmd = ''
            self.cmd2 = ''
            return
        self.histpos = self.histpos + 1
        self.history.append('')
        self.cmd = self.cmd + l
        self.cmd2 = self.cmd2 + remQuotStr(l)
        l = string.rstrip(l)
        if not bracketsBalanced(self.cmd2) or l[-1] == ':' or \
                        l[-1] == '\\' or l[0] in ' \11':
            self.prompt.set_text(sys.ps2)
            self.prompt.queue_draw()
            return
        self.run(self.cmd)
        self.cmd = ''
        self.cmd2 = ''

    def run(self, cmd):
        sys.stdout, self.stdout = self.stdout, sys.stdout
        sys.stderr, self.stderr = self.stderr, sys.stderr
        try:
            try:
                r = eval(cmd, self.namespace, self.namespace)
                if r is not None:
                    print(repr(r))
            except SyntaxError:
                exec(cmd, self.namespace)
        except:
            if hasattr(sys, 'last_type') and \
                            sys.last_type == SystemExit:
                self.quit()
            else:
                traceback.print_exc()
        self.prompt.set_text(sys.ps1)
        self.prompt.queue_draw()
        sys.stdout, self.stdout = self.stdout, sys.stdout
        sys.stderr, self.stderr = self.stderr, sys.stderr

def gtk_console(ns, title='Python', copyright='', menu=None):
    win = gtk.Window()
    win.set_size_request(475, 300)
    win.connect("destroy", lambda w: gtk.main_quit())
    win.connect("delete_event", lambda w,e: gtk.main_quit())
    win.set_title(title)
    cons = Console(namespace=ns, copyright=copyright,
                   quit_cb=lambda w: gtk.main_quit())
    if menu:
        box = gtk.VBox()
        win.add(box)
        box.show()
        box.pack_start(menu, expand=False)
        menu.show()
        box.pack_start(cons)
    else:
        win.add(cons)
    cons.show()
    win.show()
    win.set_size_request(0,0)
    cons.init()
    gtk.main()

if __name__ == '__main__':
    gtk_console({'__builtins__': __builtins__, '__name__': '__main__',
            '__doc__': None})
