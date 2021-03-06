#!/usr/bin/python

# Tiny Syslog Server in Python.
##
# This is a tiny syslog server that is able to receive UDP based syslog
# entries on a specified port and save them to a HotQueue in Redis
#
# Org file at https://gist.github.com/marcelom/4218010
#

import click
import sys
import os
import traceback
import socket
import SocketServer
import time
# from make_colors import make_colors
import termcolor
import colorama
import re
from datetime import datetime
import syslog
import time
import ConfigParser
from debug import debug
PID = os.getpid()
HOST, PORT = "0.0.0.0", 514

lineNumber = 1


class SyslogUDPHandler(SocketServer.BaseRequestHandler):
    
    def make_colors_click(self, string, foreground='', background=''):
        return click.secho(string, fg=foreground, bg=background)

    def make_colors(self, string, foreground = '', background = '', attrs = ''):
        string = str(string)
        try:
            colorama.init(True, wrap= True)
            if sys.platform == 'win32':
                colors_fore = {
                    "white": colorama.Fore.WHITE,
                    "black": colorama.Fore.BLACK,
                    "blue": colorama.Fore.BLUE,
                    "cyan": colorama.Fore.CYAN,
                    "green": colorama.Fore.GREEN,
                    "red": colorama.Fore.RED,
                    "magenta": colorama.Fore.MAGENTA,
                    "yellow": colorama.Fore.YELLOW,
                    "lightwhite": colorama.Fore.LIGHTWHITE_EX,
                    "lightblack": colorama.Fore.LIGHTBLACK_EX,
                    "lightblue": colorama.Fore.LIGHTBLUE_EX,
                    "lightcyan": colorama.Fore.LIGHTCYAN_EX,
                    "lightgreen": colorama.Fore.LIGHTGREEN_EX,
                    "lightred": colorama.Fore.LIGHTRED_EX,
                    "lightmagenta": colorama.Fore.LIGHTMAGENTA_EX,
                    "lightyellow": colorama.Fore.LIGHTYELLOW_EX,                    
                }
                
                colors_back = {
                    'white': colorama.Back.WHITE,
                    'black': colorama.Back.BLACK,
                    'blue': colorama.Back.BLUE,
                    'cyan': colorama.Back.CYAN,
                    'green': colorama.Back.GREEN,
                    'red': colorama.Back.RED,
                    'magenta': colorama.Back.MAGENTA,
                    'yellow': colorama.Back.YELLOW,
                    'lightwhite': colorama.Back.LIGHTWHITE_EX,
                    'lightblack': colorama.Back.LIGHTBLACK_EX,
                    'lightblue': colorama.Back.LIGHTBLUE_EX,
                    'lightcyan': colorama.Back.LIGHTCYAN_EX,
                    'lightgreen': colorama.Back.LIGHTGREEN_EX,
                    'lightred': colorama.Back.LIGHTRED_EX,
                    'lightmagenta': colorama.Back.LIGHTMAGENTA_EX,
                    'lightyellow': colorama.Back.LIGHTYELLOW_EX,                    
                }
            else:
                colors_fore = {
                    "white": colorama.Fore.WHITE,
                    "black": colorama.Fore.BLACK,
                    "blue": colorama.Fore.BLUE,
                    "cyan": colorama.Fore.CYAN,
                    "green": colorama.Fore.GREEN,
                    "red": colorama.Fore.RED,
                    "magenta": colorama.Fore.MAGENTA,
                    "yellow": colorama.Fore.YELLOW,
                    "lightwhite": colorama.Fore.white,
                    "lightblack": colorama.Fore.black,
                    "lightblue": colorama.Fore.blue,
                    "lightcyan": colorama.Fore.cyan,
                    "lightgreen": colorama.Fore.green,
                    "lightred": colorama.Fore.red,
                    "lightmagenta": colorama.Fore.magenta,
                    "lightyellow": colorama.Fore.yellow,                    
                }
                
                colors_back = {
                    'white': colorama.Back.WHITE,
                    'black': colorama.Back.BLACK,
                    'blue': colorama.Back.BLUE,
                    'cyan': colorama.Back.CYAN,
                    'green': colorama.Back.GREEN,
                    'red': colorama.Back.RED,
                    'magenta': colorama.Back.MAGENTA,
                    'yellow': colorama.Back.YELLOW,
                    "lightwhite": colorama.Fore.white,
                    "lightblack": colorama.Fore.black,
                    "lightblue": colorama.Fore.blue,
                    "lightcyan": colorama.Fore.cyan,
                    "lightgreen": colorama.Fore.green,
                    "lightred": colorama.Fore.red,
                    "lightmagenta": colorama.Fore.magenta,
                    "lightyellow": colorama.Fore.yellow,
                }
            
            foreground1 = colors_fore.get(str(foreground))
            background1 = colors_back.get(str(background))

            if not foreground1:
                foreground1 = ''
            if not background1:
                background1 = ''
            if foreground == None or background == "None":
                return string
            colorama.reinit()
            return foreground1 + background1 + string 
        except ImportError:
            print 'NO MODULE NAME: "colorama"'
            return string
        # colorama.init()

    def sent_to_broker(self, newLogString, host="localhost", port=6379, db=1):
        '''function sent_to_broker
        
        sent message/text string to broker (rabbitmq, etc)
        
        Keyword Arguments:
            newLogString {str} -- [description] (default: {"localhost"})
            host {str} -- [description] (default: {"localhost"})
            port {number} -- [description] (default: {6379})
            db {number} -- [description] (default: {1})
        '''
        if self.read_config('QUEUE', 'host'):
            host = self.read_config('QUEUE', 'host')
        if self.read_config('QUEUE', 'port'):
            port = int(self.read_config('QUEUE', 'port'))
        from hotqueue import HotQueue
        queue = HotQueue("logqueue", host=host, port=port, db=db)
        queue.put(newLogString)

    def convert_priority_to_severity(self, number):
        try:
            facility = int(number) / 8
            total_faciliy = facility*8
            severity = int(number) - total_faciliy
            return severity
        except:
            return 8

    def coloring(self, number, text, facility_string=''):
        '''function coloring
        
        Convert priority number and message then colored
        
        Arguments:
            number {str} -- number include from syslog receive
            text {str} -- text string syslog receiver per line/time
        
        Returns:
             str -- message/text with colored
        '''
        if facility_string:
            facility_string = self.make_colors("[", 'white') + self.make_colors(facility_string, 'green') + self.make_colors("]", 'white') + " "
        severity = self.convert_priority_to_severity(number)
        # print "severity =", severity
        if int(severity) == 0:
            return facility_string + self.make_colors(text, 'white', 'magenta')
        elif int(severity) == 1:
            return facility_string + self.make_colors(text, 'white', 'blue')
        elif int(severity) == 2:
            return facility_string + self.make_colors(text, 'white', 'green')
        elif int(severity) == 3:
            return facility_string + self.make_colors(text, 'white', 'red')
        elif int(severity) == 4:
            return facility_string + self.make_colors(text, 'white', 'yellow')
        elif int(severity) == 5:
            return facility_string + self.make_colors(text, 'white', 'cyan')
        elif int(severity) == 6:
            return facility_string + self.make_colors(text, 'green')
        elif int(severity) == 7:
            return facility_string + self.make_colors(text, 'yellow')
        else:
            return facility_string + self.make_colors(text, 'red', 'white')

    def set_config(self, file_config_path='psyslog.ini'):
        import ConfigParser
        cfg = ConfigParser.RawConfigParser(allow_no_value=True)
        cfg.optionxform = str
        if not os.path.isfile(file_config_path):
            f = open(file_config_path, 'w')
            f.close()
        return cfg, file_config_path

    def read_config(self, section, option, value=''):
        """
            option: section, option, filename='', value=None
        """
        cfg, config_file = self.set_config()
        cfg.read(config_file)
        
        try:
            data = cfg.get(section, option)
        except:
            try:
                self.write_config(section, option, value)
            except:
                # pass
                traceback.format_exc()
            try:
                data = cfg.get(section, option)
            except:
                return ''
        return data

    def write_config(self, section, option, value):
        cfg, config_file = self.set_config()
        if cfg:
            cfg.read(config_file)
        
        try:
            cfg.set(section, option, value)
        except ConfigParser.NoSectionError:
            cfg.add_section(section)
            cfg.set(section, option, value)
        cfg_data = open(config_file,'wb')
        cfg.write(cfg_data) 
        cfg_data.close()  

        # import configset
        # configset.write_config(section, option, config_file, value)
        # # try:
        # #     cfg.set(section, option, value)
        # # except ConfigParser.NoSectionError:
        # #     cfg.add_section(section)
        # #     cfg.set(section, option, value)
        # # cfg_data = open(config_file,'wb')
        # # cfg.write(cfg_data) 
        # # cfg_data.close()

    def convert_time(self, time):
        '''function convert time
        
        Convert Integer to strftime {string} time
        based on format
        
        Arguments:
            time {int} -- integer timstamps
        
        Returns:
            string -- format: 'YEAR:MONT:DAY HOUR:MINUTE:SECOND:MILISECOND'
        '''
        x = datetime.fromtimestamp(time)
        # ct = self.make_colors(datetime.strftime(x, '%Y:%m:%d %H:%M:%S.%f'), 'magenta')
        return datetime.strftime(x, '%Y:%m:%d %H:%M:%S.%f')

    def time_to_integer(self, timestamps):
        return time.mktime(timestamps.timetuple())

    def save_to_file(self, message, timestamps, facility_string='', logfile_name='psyslog.log', rotate='1M'):
        if not self.read_config('LOGS', 'rotate'):
            self.write('LOGS', 'rotate', rotate)
        if facility_string:
            facility_string = " [" + facility_string + "] "
        message = timestamps + facility_string + message + "\n"
        if os.path.isfile(logfile_name):
            with open(logfile_name, 'a') as logfile:
                logfile.write(message)
        else:
            with open(logfile_name, 'w') as logfile:
                logfile.write(message)
        
        # if rotate:
        #     if self.read_config('LOGS', 'start'):
        #         divider = datetime.datetime(1970,1,1)
        #         seconds_start = (datetime.strptime(self.read_config('LOGS', 'start'), '%Y:%m:%d %H:%M:%S.%f').timetuple()-divider).days
        #         seconds_now = (datetime.datetime.fromtimestamp(time.time()).timetuple()-divider).days
        #         all_days = seconds_now - seconds_start
        #     else:
        #         start = datetime.strftime(datetime.now(), '%Y:%m:%d %H:%M:%S')
        #         self.write('LOGS', 'start', start)
        #         return self.test_rotate_time()

    # def handle(self, show_priority=False, send_queue=False, save_to_database=False, save_to_file=False, database_type='sqlite', max_line=9999, show_priority_number=True):
    def handle(self):
        global lineNumber
        show_priority = self.read_config('GENERAL', 'show_priority')
        send_queue = self.read_config('GENERAL', 'send_queue')
        save_to_database = self.read_config('GENERAL', 'save_to_database')
        save_to_file = self.read_config('GENERAL', 'save_to_file')
        database_type = self.read_config('DATABASE', 'database_type')
        log_file_name = self.read_config('LOGS', 'log_file_name')
        max_line = self.read_config('LOGS', 'max_line')
        rotate = self.read_config('LOGS', 'rotate')
        show_priority_number = self.read_config('GENERAL', 'show_priority_number')

        # print "show_priority =", show_priority
        # print "send_queue =", send_queue
        # print "save_to_database =", save_to_database
        # print "save_to_file =", save_to_file
        # print "database_type =", database_type
        # print "max_line =", max_line
        # print "show_priority_number =", show_priority_number

        if not show_priority:
            # print "NOT show_priority"
            self.write_config('GENERAL', 'show_priority', '')
        else:
            show_priority = bool(show_priority)
        if not send_queue:
            # print "NOT send_queue"
            self.write_config('GENERAL', 'send_queue', '')
        else:
            send_queue = bool(send_queue)
        if not save_to_database:
            # print "NOT save_to_database"
            self.write_config('GENERAL', 'save_to_database', '')
        else:
            save_to_database = bool(save_to_database)    
        if not save_to_file:
            # print "NOT save_to_file"
            self.write_config('GENERAL', 'save_to_file', '')
        else:
            save_to_file = bool(save_to_file)
        if not database_type:
            # print "NOT database_type"
            self.write_config('DATABASE', 'database_type', 'sqlite')
        if not log_file_name:
            # print "Not log_file_name"
            self.write_config('LOGS', 'log_file_name', 'psyslog.log')
        if not max_line:
            # print "NOT max_line"
            self.write_config('LOGS', 'max_line', 9999)
        if not rotate:
            # print "NOT rotate"
            self.write_config('LOGS', 'rotate', '1M')
        if not show_priority_number:
            # print "NOT show_priority_number"
            self.write_config('GENERAL', 'show_priority_number', '')
        else:
            show_priority_number = bool(show_priority_number)

        client_address = self.make_colors(self.client_address[0], 'cyan')
        times = self.convert_time(int(time.time()))
        data = bytes.decode(self.request[0].strip(), 'utf-8')
        data_split = re.split('<|>', data, 2)
        # print "data_split =",data_split
        if data_split[0] == u'':
            number = data_split[1]
            message = " ".join(data_split[2:]).strip()
        else:
            number = data_split[0]
            message = " ".join(data_split[1:]).strip()
        # print "number =", number
        if show_priority:
            facility_string = syslog.FACILITY.get(int(self.convert_priority_to_severity(number)))
            if show_priority_number:
                data = self.coloring(number, data, facility_string)
            else:
                data = self.coloring(number, message, facility_string)
        data = self.coloring(number, data)
        laengde = len(data)
        if laengde > 4:
            newLogString = "%s@%s %s %s" % (self.make_colors(lineNumber, 'green'), times, client_address, data)
            if send_queue:
                newLogString = "%s@%s %s %s\n" % (lineNumber, times, self.client_address[0], data)
                self.sent_to_broker(newLogString)
            try:
                print newLogString
            except:
        
                print "%s@%s %s %s" % (lineNumber, times, self.client_address[0], message)
            if save_to_file:
                self.save_to_file(message, times, facility_string, log_file_name, rotate)
            lineNumber += 1

        # if lineNumber > 10000000:
        if lineNumber > max_line:
            if sys.platform == 'win32':
                os.system('cls')
            else:
                os.system('clear')
            lineNumber = 1

class Psyslog(object):
    def __init__(self):
        super(Psyslog, self)

    def make_colors(self, string, foreground = '', background = '', attrs = ''):
        string = str(string)
        try:
            colorama.init(True, wrap= True)
            if sys.platform == 'win32':
                colors_fore = {
                    "white": colorama.Fore.WHITE,
                    "black": colorama.Fore.BLACK,
                    "blue": colorama.Fore.BLUE,
                    "cyan": colorama.Fore.CYAN,
                    "green": colorama.Fore.GREEN,
                    "red": colorama.Fore.RED,
                    "magenta": colorama.Fore.MAGENTA,
                    "yellow": colorama.Fore.YELLOW,
                    "lightwhite": colorama.Fore.LIGHTWHITE_EX,
                    "lightblack": colorama.Fore.LIGHTBLACK_EX,
                    "lightblue": colorama.Fore.LIGHTBLUE_EX,
                    "lightcyan": colorama.Fore.LIGHTCYAN_EX,
                    "lightgreen": colorama.Fore.LIGHTGREEN_EX,
                    "lightred": colorama.Fore.LIGHTRED_EX,
                    "lightmagenta": colorama.Fore.LIGHTMAGENTA_EX,
                    "lightyellow": colorama.Fore.LIGHTYELLOW_EX,                    
                }
                
                colors_back = {
                    'white': colorama.Back.WHITE,
                    'black': colorama.Back.BLACK,
                    'blue': colorama.Back.BLUE,
                    'cyan': colorama.Back.CYAN,
                    'green': colorama.Back.GREEN,
                    'red': colorama.Back.RED,
                    'magenta': colorama.Back.MAGENTA,
                    'yellow': colorama.Back.YELLOW,
                    'lightwhite': colorama.Back.LIGHTWHITE_EX,
                    'lightblack': colorama.Back.LIGHTBLACK_EX,
                    'lightblue': colorama.Back.LIGHTBLUE_EX,
                    'lightcyan': colorama.Back.LIGHTCYAN_EX,
                    'lightgreen': colorama.Back.LIGHTGREEN_EX,
                    'lightred': colorama.Back.LIGHTRED_EX,
                    'lightmagenta': colorama.Back.LIGHTMAGENTA_EX,
                    'lightyellow': colorama.Back.LIGHTYELLOW_EX,                    
                }
            else:
                colors_fore = {
                    "white": colorama.Fore.WHITE,
                    "black": colorama.Fore.BLACK,
                    "blue": colorama.Fore.BLUE,
                    "cyan": colorama.Fore.CYAN,
                    "green": colorama.Fore.GREEN,
                    "red": colorama.Fore.RED,
                    "magenta": colorama.Fore.MAGENTA,
                    "yellow": colorama.Fore.YELLOW,
                    "lightwhite": colorama.Fore.white,
                    "lightblack": colorama.Fore.black,
                    "lightblue": colorama.Fore.blue,
                    "lightcyan": colorama.Fore.cyan,
                    "lightgreen": colorama.Fore.green,
                    "lightred": colorama.Fore.red,
                    "lightmagenta": colorama.Fore.magenta,
                    "lightyellow": colorama.Fore.yellow,                    
                }
                
                colors_back = {
                    'white': colorama.Back.WHITE,
                    'black': colorama.Back.BLACK,
                    'blue': colorama.Back.BLUE,
                    'cyan': colorama.Back.CYAN,
                    'green': colorama.Back.GREEN,
                    'red': colorama.Back.RED,
                    'magenta': colorama.Back.MAGENTA,
                    'yellow': colorama.Back.YELLOW,
                    "lightwhite": colorama.Fore.white,
                    "lightblack": colorama.Fore.black,
                    "lightblue": colorama.Fore.blue,
                    "lightcyan": colorama.Fore.cyan,
                    "lightgreen": colorama.Fore.green,
                    "lightred": colorama.Fore.red,
                    "lightmagenta": colorama.Fore.magenta,
                    "lightyellow": colorama.Fore.yellow,
                }
            
            foreground1 = colors_fore.get(str(foreground))
            background1 = colors_back.get(str(background))

            if not foreground1:
                foreground1 = ''
            if not background1:
                background1 = ''
            if foreground == None or background == "None":
                return string
            colorama.reinit()
            return foreground1 + background1 + string 
        except ImportError:
            print 'NO MODULE NAME: "colorama"'
            return string
        # colorama.init()

    def sent_to_broker(self, newLogString, host="localhost", port=6379, db=1):
        '''function sent_to_broker
        
        sent message/text string to broker (rabbitmq, etc)
        
        Keyword Arguments:
            newLogString {str} -- [description] (default: {"localhost"})
            host {str} -- [description] (default: {"localhost"})
            port {number} -- [description] (default: {6379})
            db {number} -- [description] (default: {1})
        '''
        if self.read_config('QUEUE', 'host'):
            host = self.read_config('QUEUE', 'host')
        if self.read_config('QUEUE', 'port'):
            port = int(self.read_config('QUEUE', 'port'))
        from hotqueue import HotQueue
        queue = HotQueue("logqueue", host=host, port=port, db=db)
        queue.put(newLogString)

    def convert_priority_to_severity(self, number):
        try:
            facility = int(number) / 8
            total_faciliy = facility*8
            severity = int(number) - total_faciliy
            return severity
        except:
            return 8

    def coloring(self, number, text, facility_string=''):
        '''function coloring
        
        Convert priority number and message then colored
        
        Arguments:
            number {str} -- number include from syslog receive
            text {str} --string syslog receiver per line/time
        
        Returns:
             str -- message/text with colored
        '''
        if facility_string:
            facility_string = self.make_colors("[", 'white', 'black') + self.make_colors(facility_string, 'magenta') + self.make_colors("]", 'white') + " "
        severity = self.convert_priority_to_severity(number)
        # print "severity =", severity
        if int(severity) == 0:
            return facility_string + self.make_colors(text, 'white', 'magenta')
        elif int(severity) == 1:
            return facility_string + self.make_colors(text, 'white', 'blue')
        elif int(severity) == 2:
            return facility_string + self.make_colors(text, 'white', 'green')
        elif int(severity) == 3:
            return facility_string + self.make_colors(text, 'white', 'red')
        elif int(severity) == 4:
            return facility_string + self.make_colors(text, 'white', 'yellow')
        elif int(severity) == 5:
            return facility_string + self.make_colors(text, 'white', 'cyan')
        elif int(severity) == 6:
            return facility_string + self.make_colors(text, 'green')
        elif int(severity) == 7:
            return facility_string + self.make_colors(text, 'yellow')
        else:
            return facility_string + self.make_colors(text, 'red', 'white')

    def set_config(self, file_config_path='psyslog.ini'):
        import ConfigParser
        cfg = ConfigParser.RawConfigParser(allow_no_value=True)
        cfg.optionxform = str
        if not os.path.isfile(file_config_path):
            f = open(file_config_path, 'w')
            f.close()
        return cfg, file_config_path

    def read_config(self, section, option, value=''):
        """
            option: section, option, filename='', value=None
        """
        cfg, config_file = self.set_config()
        cfg.read(config_file)
        
        try:
            data = cfg.get(section, option)
        except:
            try:
                self.write_config(section, option, value)
            except:
                # pass
                traceback.format_exc()
            try:
                data = cfg.get(section, option)
            except:
                return ''
        return data

    def write_config(self, section, option, value):
        cfg, config_file = self.set_config()
        if cfg:
            cfg.read(config_file)
        
        try:
            cfg.set(section, option, value)
        except ConfigParser.NoSectionError:
            cfg.add_section(section)
            cfg.set(section, option, value)
        cfg_data = open(config_file,'wb')
        cfg.write(cfg_data) 
        cfg_data.close()  

        # import configset
        # configset.write_config(section, option, config_file, value)
        # # try:
        # #     cfg.set(section, option, value)
        # # except ConfigParser.NoSectionError:
        # #     cfg.add_section(section)
        # #     cfg.set(section, option, value)
        # # cfg_data = open(config_file,'wb')
        # # cfg.write(cfg_data) 
        # # cfg_data.close()

    def convert_time(self, time):
        '''function convert time
        
        Convert Integer to strftime {string} time
        based on format
        
        Arguments:
            time {int} -- integer timstamps
        
        Returns:
            string -- format: 'YEAR:MONT:DAY HOUR:MINUTE:SECOND:MILISECOND'
        '''
        x = datetime.fromtimestamp(time)
        # ct = self.make_colors(datetime.strftime(x, '%Y:%m:%d %H:%M:%S.%f'), 'magenta')
        return datetime.strftime(x, '%Y:%m:%d %H:%M:%S.%f')

    def time_to_integer(self, timestamps):
        return time.mktime(timestamps.timetuple())

    def save_to_file(self, message, timestamps, facility_string='', logfile_name='psyslog.log', rotate='1M'):
        if not self.read_config('LOGS', 'rotate'):
            self.write('LOGS', 'rotate', rotate)
        if facility_string:
            facility_string = " [" + facility_string + "] "
        message = timestamps + facility_string + message + "\n"
        if os.path.isfile(logfile_name):
            with open(logfile_name, 'a') as logfile:
                logfile.write(message)
        else:
            with open(logfile_name, 'w') as logfile:
                logfile.write(message)
        
        # if rotate:
        #     if self.read_config('LOGS', 'start'):
        #         divider = datetime.datetime(1970,1,1)
        #         seconds_start = (datetime.strptime(self.read_config('LOGS', 'start'), '%Y:%m:%d %H:%M:%S.%f').timetuple()-divider).days
        #         seconds_now = (datetime.datetime.fromtimestamp(time.time()).timetuple()-divider).days
        #         all_days = seconds_now - seconds_start
        #     else:
        #         start = datetime.strftime(datetime.now(), '%Y:%m:%d %H:%M:%S')
        #         self.write('LOGS', 'start', start)
        #         return self.test_rotate_time()

    # def handle(self, show_priority=False, send_queue=False, save_to_database=False, save_to_file=False, database_type='sqlite', max_line=9999, show_priority_number=True):

    def server(self, host='0.0.0.0', port=1514):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            sock.bind((host, port))
            # sock.listen(5)
            print "Syslog Bind: %s:%s [pid:%s]" %(self.make_colors(host, 'green'), self.make_colors(str(port), 'cyan'), self.make_colors(PID, 'red'))
            while 1:
                data = sock.recv(65565)
                if data:
                    if data == 'EXIT':
                        sys.exit('server shutdown ....')
                    print data
                    # print "data =", data
                    # print "client_address =", client_address
                    # print self.handle(data, client_address)
        except SystemExit:
            sys.exit('SYSTEM EXIT !')
        except:
            traceback.format_exc()
            
    def handle(self, data, client_address):
        pid = os.getpid()
        global lineNumber
        show_priority = self.read_config('GENERAL', 'show_priority')
        send_queue = self.read_config('GENERAL', 'send_queue')
        save_to_database = self.read_config('GENERAL', 'save_to_database')
        save_to_file = self.read_config('GENERAL', 'save_to_file')
        database_type = self.read_config('DATABASE', 'database_type')
        log_file_name = self.read_config('LOGS', 'log_file_name')
        max_line = self.read_config('LOGS', 'max_line')
        rotate = self.read_config('LOGS', 'rotate')
        debugger = self.read_config('DEBUG', 'debug')
        debugger_server = self.read_config('DEBUG', 'debug_server')
        show_priority_number = self.read_config('GENERAL', 'show_priority_number')

        debug(show_priority1=show_priority)
        debug(send_queue1=send_queue)
        debug(save_to_file1=save_to_file)
        debug(save_to_database1=save_to_database)
        debug(database_type1=database_type)
        debug(log_file_name1=log_file_name)
        debug(max_line1=max_line)
        debug(rotate1=rotate)
        debug(debugger1=debugger)
        debug(debugger_server1=debugger_server)
        debug(show_priority_number1=show_priority_number)

        if not debugger:
            self.write_config('DEBUG', 'debug', '')
        else:
            debugger = bool(debugger)
        if not debugger_server:
            self.write_config('DEBUG', 'debugger_server', '127.0.0.1:50001')
            os.environ.update({'DEBUG_SERVER':'1'})    
            os.environ.update({'DEBUGGER_SERVER':'127.0.0.1:50001'})
        else:
            os.environ.update({'DEBUG_SERVER':'1'})    
            os.environ.update({'DEBUGGER_SERVER':debugger_server})
        
        if not show_priority:
            self.write_config('GENERAL', 'show_priority', '')
        else:
            show_priority = bool(show_priority)
        if not send_queue:
            self.write_config('GENERAL', 'send_queue', '')
        else:
            send_queue = bool(send_queue)
        if not save_to_database:
            self.write_config('GENERAL', 'save_to_database', '')
        else:
            save_to_database = bool(save_to_database)    
        if not save_to_file:
            self.write_config('GENERAL', 'save_to_file', '')
        else:
            save_to_file = bool(save_to_file)
        if not database_type:
            self.write_config('DATABASE', 'database_type', 'sqlite')
        if not log_file_name:
            self.write_config('LOGS', 'log_file_name', 'psyslog.log')
        if not max_line:
            self.write_config('LOGS', 'max_line', 9999)
        if not rotate:
            self.write_config('LOGS', 'rotate', '1M')
        if not show_priority_number:
            self.write_config('GENERAL', 'show_priority_number', '')
        else:
            show_priority_number = bool(show_priority_number)

        debug(show_priority2=show_priority)
        debug(send_queue2=send_queue)
        debug(save_to_file2=save_to_file)
        debug(save_to_database2=save_to_database)
        debug(database_type2=database_type)
        debug(log_file_name2=log_file_name)
        debug(max_line2=max_line)
        debug(rotate2=rotate)
        debug(debugger2=debugger)
        debug(debugger_server2=debugger_server)
        debug(show_priority_number2=show_priority_number)

        try:
            client_address = self.make_colors(client_address[0], 'cyan')
            times = self.make_colors(self.convert_time(int(time.time())), 'white', 'black')
            data_split = re.split('<|>', data, 2)
            debug(data_split=data_split)
            if data_split[0] == u'':
                number = data_split[1]
                message = " ".join(data_split[2:]).strip()
            else:
                number = data_split[0]
                message = " ".join(data_split[1:]).strip()
            debug(number=number)
            debug(message=message)
            if show_priority:
                facility_string = syslog.FACILITY.get(int(self.convert_priority_to_severity(number)))
                if show_priority_number:
                    data = self.coloring(number, data, facility_string)
                else:
                    data = self.coloring(number, message, facility_string)
            data = self.coloring(number, data)
            debug(data=data)
            laengde = len(data)
            debug(laengde=laengde)
            if laengde > 4:
                newLogString = "%s%s%s %s %s [%s]" % (self.make_colors(lineNumber, 'yellow'), self.make_colors('@', 'red'), times, client_address, data, str(pid))
                if send_queue:
                    newLogString = "%s@%s %s %s\n" % (lineNumber, times, client_address[0], data)
                    self.sent_to_broker(newLogString)
                if lineNumber > max_line:
                    debug(lineNumber=lineNumber)
                    if sys.platform == 'win32':
                        os.system('cls')
                    else:
                        os.system('clear')
                    lineNumber = 1

                if save_to_file:
                    self.save_to_file(message, times, facility_string, log_file_name, rotate)
                lineNumber += 1

            # if lineNumber > 10000000:
            # return newLogString
            # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return newLogString

        except KeyboardInterrupt:
            print "Closing .. by user"
            sys.exit(0)
        except:
            traceback.format_exc()
            print "Closing .. by system"
            sys.exit(0)

    def client(self, host='0.0.0.0', port=514, server_port=1514):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((host, port))
            print "Syslog Client Bind: %s:%s [%s]" %(self.make_colors(host, 'green'), self.make_colors(str(port), 'cyan'), PID)
            while 1:
                data, client_address = sock.recvfrom(65565)
                if data:
                    if data == 'EXIT':
                        sys.exit('server shutdown ....')
                    data = self.handle(data, client_address)
                    sock.sendto(data, ('127.0.0.1', server_port))
        except:
            sock.close()
            traceback.format_exc()
            print "Closing .. by system"
            sys.exit('SYSTEM EXIT !')

    def shutdown(self, host='127.0.0.1', port=514):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto("EXIT", (host, port))
        s.close()

    def usage(self):
        import argparse
        parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('-s', '--server', action='store_true', help='run server')
        parser.add_argument('-c', '--client', action='store_true', help='run client server')
        parser.add_argument('-H', '--host', action='store', help='Host binding default:0.0.0.0 -- all network interface', default='0.0.0.0')
        parser.add_argument('-P', '--client-port', action='store', help='Port binding default: 514', default=514)
        parser.add_argument('-S', '--server-port', action='store', help='Port binding default: 1514', default=1514)
        parser.add_argument('-x', '--exit', action='store_true', help='shutdown/terminate server')
        if len(sys.argv) == 1:
            parser.print_help()
        else:
            args = parser.parse_args()
            if args.server:
                self.server(args.host, args.server_port)
            if args.client:
                self.client(args.host, args.client_port)
            if args.exit:
                if args.server:
                    self.shutdown('127.0.0.1', args.server_port)
                elif args.client:
                    self.shutdown('127.0.0.1', args.client_port)
                else:
                    self.shutdown('127.0.0.1', args.server_port)                
                    self.shutdown('127.0.0.1', args.client_port)

def run1():
    try:
        server = SocketServer.UDPServer((HOST, PORT), SyslogUDPHandler)
        server.serve_forever()
    except (IOError, SystemExit):
        pass
    except KeyboardInterrupt:
        print("Crtl+C Pressed. Shutting down.")

def run2():
    try:
        c = Psyslog()
        c.handle()
    except KeyboardInterrupt:
        print "Closing .. by user"
        sys.exit(0)
    except:
        traceback.format_exc()
        print "Closing .. by system"
        sys.exit(0)


if __name__ == "__main__":
    c = Psyslog()
    c.usage()