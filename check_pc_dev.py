#!/usr/bin/env python3
import os
import pexpect
from tkinter import *
import time
import threading


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
            if 'part' not in line and 'ata' in line or 'nv' in line:
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
        sort_key = ("CPU",'主板','内存','硬盘')
        for key in sort_key:
            self.create_label(self.fm2_part, text=key, font=12)
            for dev_produce in self.dct_dev[key]:
                dev_produce = "  " + dev_produce
                self.create_label(self.fm2_part, text=dev_produce)
        self.fm2_part.pack(anchor=W)

    def cpu_stress(self):
        new_dia = Toplevel()
        x_pos, y_pos = self.new_win_get_master_place(150, 150)
        new_dia.geometry('500x70+%s+%s' % (x_pos, y_pos))
        new_dia.title('save check')
        CpuStress(new_dia)
        self.master.wait_window(new_dia)

    def display_test(self):
        pass

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


class CpuStress:
    def __init__(self, master):
        self.time = 0
        self.master = master
        num = 300
        # self.flag = True
        self.show_time(num)
        self.show_tem()
        self.cpu_stress()
        master.protocol("WM_DELETE_WINDOW", self.gui_exit)

    def _show_time(self, num):
        time_fm = Frame(self.master)
        var_start = StringVar()
        var_start.set('计时器：'+str(num))
        label = Label(time_fm, textvariable=var_start, font=50)
        label.pack(side=LEFT, anchor=N)
        time_fm.pack(anchor=W)
        i = 0
        while True:
            var_start.set('计时器：'+str(num - i))
            time.sleep(1)
            i += 1

    def _show_tem(self):
        fm = Frame(self.master)
        var_start = StringVar()
        var_start.set(0)
        label = Label(fm, textvariable=var_start, font=50)
        label.pack(side=LEFT, anchor=N)
        fm.pack(anchor=W)
        while True:
            tmp = self.get_tem()
            var_start.set('温度：'+tmp)
            time.sleep(1)

    def get_tem(self):
        cmd = 'sensors'
        key_word = 'temp1:'
        return check_dev(cmd, key_word)

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

    def gui_exit(self):
        cmd = 'pkill gzip'
        os.popen(cmd)
        self.master.destroy()


if __name__ == '__main__':
    win = Tk()
    win.geometry('800x600+%s+%s' % (600, 400))
    win.title("Computer Devices")
    display = MainGui(win)
    win.mainloop()
    # print(r.dct_dev)