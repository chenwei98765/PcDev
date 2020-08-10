#!/usr/bin/env python3
import os
import pexpect
from tkinter import *
import time
import threading


COLOR_LIGHT = ["#AFAFAF","#B7B7B7","#BFBFBF","#C7C7C7","#CFCFCF","#D7D7D7","#DFDFDF","#E7E7E7","#EFEFEF","#F7F7F7",
               "#D7D7D7","#DBDBDB","#DFDFDF","#E3E3E3","#E7E7E7","#EBEBEB","#EFEFEF","#F3F3F3","#F7F7F7","#FBFBFB",
               "#EBEBEB","#EDEDED","#EFEFEF","#F1F1F1","#F3F3F3","#F5F5F5","#F7F7F7","#F9F9F9","#FBFBFB","#FDFDFD",
               "#F5F5F5","#F6F6F6","#F7F7F7","#F8F8F8","#F9F9F9","#FAFAFA","#FBFBFB","#FCFCFC","#FDFDFD","#FEFEFE"]
COLOR_DARK = ["#010101","#020202","#030303","#040404","#050505","#060606","#070707","#080808","#090909","#0A0A0A",
               "#020202","#040404","#060606","#080808","#0A0A0A","#0C0C0C","#0E0E0E","#101010","#121212","#141414",
               "#040404","#080808","#0C0C0C","#101010","#141414","#181818","#1C1C1C","#202020","#242424","#282828",
               "#080808","#101010","#181818","#202020","#282828","#303030","#383838","#404040","#484848","#505050"]

def check_dev(cmd, key_word):
    rst = os.popen(cmd)
    for line in rst.readlines():
        line = line.strip('\n').strip(' ')
        if key_word in line:
            return line.strip(key_word)


def sudo_cmd(cmd, password='1'):
    if "sudo" not in cmd:
        cmd = "sudo " + cmd
    process = pexpect.spawn(cmd, timeout=600, maxread=10240)
    process.expect('password')
    process.sendline(password)
    return process.readlines()


def get_value(line, start_word, end_word=""):
    # 可以使用正则来做
    start_no = line.find(start_word) + len(start_word)
    if start_no < 0:
        return ""
    other = line[start_no:]
    if end_word != "":
        if end_word not in other:
            return ""
        end_no = other.find(end_word)
    else:
        end_no = len(other)
    return other[:end_no].strip('\n').strip('\r')


class ReadDev:
    def __init__(self):
        self.dct_dev = {}

    def get_cpu(self):
        # 也可以从dmidecode里获取
        cmd = "cat /proc/cpuinfo"
        key_word = 'model name	: '
        cpu_info = check_dev(cmd, key_word)
        self.dct_dev.update({'CPU': [cpu_info]})

    def get_graphics(self):
        cmd = "lspci -vv"
        key_word0 = 'VGA compatible controller:'
        key_word1 = 'Subsystem: '
        rst = os.popen(cmd)
        flag = False
        lst_graphics = []
        for line in rst.readlines():
            line = line.strip('\n').strip(' ')
            if key_word0 in line:
                vga_type = get_value(line, key_word0)
                flag = True
            if flag:
                if key_word1 in line:
                    vga_cro = get_value(line, key_word1)
                    lst_graphics.append("品牌：%s  型号：%s" % (vga_cro, vga_type))
                    flag = False
        self.dct_dev.update({'显卡': lst_graphics})

    def get_memory(self):
        cmd = 'dmidecode -t memory'
        rst = sudo_cmd(cmd)
        mem_data = [i.decode('utf-8').strip('\n') for i in rst]
        mem_data = '\n'.join(mem_data)
        lst_mem = mem_data.split("Memory Device")
        lst_info = []
        for i in range(1, len(lst_mem)):
            size = get_value(lst_mem[i], 'Size: ', end_word='\n')
            if "No Module Installed" in size:
                continue
            speed = get_value(lst_mem[i], 'Speed: ', end_word='\n')
            manufacturer = get_value(lst_mem[i], 'Manufacturer:', end_word='\n')
            part_number = get_value(lst_mem[i], 'Part Number:', end_word='\n')
            mem_info = "品牌：%s 容量：%s 频率：%s 编号：%s" % (manufacturer, size, speed,part_number)
            lst_info.append(mem_info)

        self.dct_dev.update({'内存': lst_info})

    def get_disk(self):
        cmd = 'ls /dev/disk/by-id'
        rst = os.popen(cmd)
        part_name = []
        for line in rst:
            line = line.strip('\n')
            if ('part' not in line and '.' not in line)and ('ata' in line or 'nvme' in line):
                part_name.append(line)
        self.dct_dev.update({'硬盘': part_name})

    def get_base_board(self):
        cmd = 'dmidecode -t baseboard'
        rst = sudo_cmd(cmd)
        flag = False
        for line in rst:
            line = line.decode('utf-8').strip('\n')
            if 'Base Board Information' in line:
                flag = True
            if flag:
                if "Manufacturer:" in line:
                    manufacturer = get_value(line, "Manufacturer: ")
                if "Product Name:" in line:
                    product_name = get_value(line, "Product Name:")
                # print(line)
                if 'Handle' in line:
                    self.dct_dev.update({'主板': ["品牌：%s 产品名称：%s" % (manufacturer, product_name)]})
                    break

    def run(self):
        self.get_memory()
        self.get_cpu()
        self.get_graphics()
        self.get_base_board()
        self.get_disk()
        return self.dct_dev

    def get_temp(self):
        cmd = 'sensors'
        rst = os.popen(cmd)
        temp = []
        for line in rst:
            if 'pch_' in line:
                temp.append('南桥芯片温度：')
            elif 'acpitz' in line:
                temp.append('ｃｐｕ接口温度')
            elif 'coretemp' in line:
                temp.append('cpu核心温度')
            else:
                temp.append(line.strip('\n'))
        return '\n'.join(temp)


def cpu_stress():
    cmd = "cat /proc/cpuinfo | grep \"processor\" | wc -l"
    rst = os.popen(cmd)
    num = int(rst.readlines()[0])
    pa = '| gzip -9 | gzip -d ' * num
    cmd = 'cat /dev/urandom %s > /dev/null' % (pa,)
    os.popen(cmd)


class MainGui:
    def __init__(self, master):
        self.dev = ReadDev()
        self.dct_dev = self.dev.run()
        self.master = master

        fm1 = Frame(master)
        self.create_fm1(fm1)
        fm1.pack(anchor=W)

        fm2 = Frame(master)
        self.fm2_part = None
        self.create_fm2(fm2)
        fm2.pack(anchor=W)

    def update_dev(self):
        self.dct_dev = self.dev.run()

    def create_fm1(self, master):
        self.create_button(master, 'CPU温度测试', self.cpu_stress)
        self.create_button(master, '显示器坏点测试', self.display_test)

    def create_fm2(self, master):
        if self.fm2_part is not None:
            self.fm2_part.destroy()
        self.fm2_part = Frame(master)
        sort_key = ("CPU",'主板','内存','硬盘','显卡')
        for key in sort_key:
            self.create_label(self.fm2_part, text=key, font=12)
            for dev_produce in self.dct_dev[key]:
                dev_produce = "  " + dev_produce
                self.create_label(self.fm2_part, text=dev_produce)
        self.fm2_part.pack(anchor=W)

    def cpu_stress(self):
        new_dia = Toplevel()
        x_pos, y_pos = self.new_win_get_master_place(150, 150)
        new_dia.geometry('500x400+%s+%s' % (x_pos, y_pos))
        new_dia.title('save check')
        CpuStress(new_dia, self.dev)
        self.master.wait_window(new_dia)

    def display_test(self):
        new_dia = Toplevel()
        DisplayTest(new_dia)
        self.master.wait_window(new_dia)

    def new_win_get_master_place(self, x_offset, y_offset):
        place = self.master.geometry()
        size, x_pos, y_pos = place.split("+")
        return int(x_pos)+x_offset, int(y_pos)+y_offset

    @staticmethod
    def create_label(master, **kw):
        fm = Frame(master)
        label = Label(fm,  **kw)
        label.pack(side=LEFT, anchor=N)
        fm.pack(anchor=W)

    @staticmethod
    def create_button(master, text, method, **kw):
        button = Button(master, text=text, width=8, command=method, **kw)
        button.pack(side=LEFT, anchor=N)


class DisplayTest:
    def __init__(self, master):
        self.master = master
        self.color_fm = None
        self.num = 0
        self.show_describe()
        master.bind("<Escape>", self.gui_exit)
        master.bind("<Button-1>", self.num_change)
        master.bind("<Button-3>", self.num_change)
        self.master.attributes("-fullscreen", True)

    def generation_color(self, color):
        if self.color_fm is not None:
            self.color_fm.destroy()
        x = self.master.winfo_screenwidth()
        y = self.master.winfo_screenheight()
        self.color_fm = Canvas(self.master, background=color, height=y, width=x)
        self.color_fm.pack(expand=1)

    def generation_change_color(self, lst_color):
        if self.color_fm is not None:
            self.color_fm.destroy()
        self.color_fm = Frame(self.master)
        self.color_fm.pack(expand=1)
        x = self.master.winfo_screenwidth()
        y = self.master.winfo_screenheight()
        dis_x = int(x / 10)
        dis_y = int(y / 4)
        index = 0
        for i in range(4):
            fm = Frame(self.color_fm)
            fm.pack(anchor=W)
            for j in range(10):
                ca = Canvas(fm, background=lst_color[index], height=dis_y, width=dis_x)
                ca.pack(side=LEFT, anchor=W)
                index += 1

    def show_red(self):
        self.generation_color('red')

    def show_green(self):
        self.generation_color('green')

    def show_white(self):
        self.generation_color('white')

    def show_black(self):
        self.generation_color('black')

    def show_yellow(self):
        self.generation_color('yellow')

    def show_blue(self):
        self.generation_color('blue')

    def show_light(self):
        self.generation_change_color(COLOR_LIGHT)

    def show_dark(self):
        self.generation_change_color(COLOR_DARK)

    def show_describe(self):
        if self.color_fm is None:
            self.color_fm = Frame(self.master)
            self.color_fm.pack(anchor=N)

        text = """显示屏开始测试，会自动调制全屏，请观察屏幕是否有明亮不连贯的地方,
                按鼠标左键前进，鼠标右键后退，按ｅｓｃ键退出测试"""
        label = Label(self.color_fm, text=text)
        label.pack(side=LEFT, anchor=N)

    def show_exit(self):
        self.gui_exit(0)

    def num_change(self, event):
        total_num = len(self.get_dct_color()) - 1
        if event.num == 1:
            self.num = min(self.num + 1, total_num)
        elif event.num == 3:
            self.num = max(self.num - 1, 0)
        self._listen_change()

    def get_dct_color(self):
        word = {0: 'describe', 1: "white", 2: 'black', 3: 'red', 4: 'green', 5: 'yellow', 6:'blue',
                7: 'light', 8: 'dark', 9: 'exit'

        }
        return word

    def _listen_change(self):
        method_name = 'show_'+self.get_dct_color()[self.num]
        method = getattr(self, method_name)
        method()

    def gui_exit(self, event):
        self.master.destroy()


class CpuStress:
    def __init__(self, master, dev_info):
        self.time = 0
        self.master = master
        self.dev_info = dev_info
        num = 300
        self.show_time(num)
        self.show_tem()
        self.cpu_stress()
        master.protocol("WM_DELETE_WINDOW", self.gui_exit)

    def _show_time(self, num):
        time_fm = Frame(self.master)
        var_start = StringVar()
        var_start.set('计时器：'+str(num))
        label = Label(time_fm, textvariable=var_start, anchor=W)
        label.pack(side=LEFT, anchor=N)
        time_fm.pack(anchor=W)
        i = 0
        while True:
            var_start.set('计时器：'+str(num - i))
            time.sleep(1)
            i += 1
            if i == num:
                var_start.set('计时器：'+str(num - i) + '压力测试结束')
                self.stop_stress()

    def _show_tem(self):
        time.sleep(0.1)
        fm = Frame(self.master)
        var_start = StringVar()
        var_start.set(0)
        label = Label(fm, textvariable=var_start, anchor=W)
        label.pack(side=LEFT, anchor=N)
        fm.pack(anchor=W)
        while True:
            tmp = self.dev_info.get_temp()
            var_start.set('温度：'+tmp)
            time.sleep(1)

    def show_tem(self):
        handle = threading.Thread(target=self._show_tem,)
        handle.daemon = True
        handle.start()

    def show_time(self, num):
        handle = threading.Thread(target=self._show_time, args=(num,))
        handle.daemon = True
        handle.start()

    def cpu_stress(self):
        handle = threading.Thread(target=cpu_stress, )
        handle.daemon = True
        handle.start()

    @staticmethod
    def stop_stress():
        cmd = 'pkill gzip'
        os.popen(cmd)

    def gui_exit(self):
        self.stop_stress()
        self.master.destroy()


if __name__ == '__main__':
    win = Tk()
    win.geometry('800x600+%s+%s' % (600, 400))
    win.title("Computer Devices")
    display = MainGui(win)
    win.mainloop()