import click
import paramiko
import sys
import os
import subprocess
import select
import socket
import termios
import tty
from itertools import zip_longest

from paramiko import sftp


class SSHClient(paramiko.SSHClient):
    def open_shell(self: paramiko.SSHClient, remote_name='SSH server'):
        oldtty_attrs = termios.tcgetattr(sys.stdin)
        channel = self.invoke_shell()

        def resize_pty():
            tty_height, tty_width = subprocess.check_output(
                ['stty', 'size']).split()

            try:
                channel.resize_pty(width=int(tty_width),
                                   height=int(tty_height))
            except paramiko.SSHException:
                pass

        try:
            stdin_fileno = sys.stdin.fileno()
            tty.setraw(stdin_fileno)
            tty.setcbreak(stdin_fileno)

            channel.settimeout(0.0)

            is_alive = True

            while is_alive:
                resize_pty()
                read_ready, write_ready, exception_list = select.select(
                    [channel, sys.stdin], [], [])
                if channel in read_ready:
                    try:
                        out = channel.recv(1024)
                        if len(out) == 0:
                            is_alive = False
                        else:
                            sys.stdout.write(out.decode())
                            sys.stdout.flush()
                    except socket.timeout:
                        pass

                if sys.stdin in read_ready and is_alive:
                    char = os.read(stdin_fileno, 1)
                    if len(char) == 0:
                        is_alive = False
                    else:
                        channel.send(char)
            channel.shutdown(2)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, oldtty_attrs)

    def run(self: paramiko.SSHClient, command):
        stdin, stdout, stderr = self.exec_command(
            command, bufsize=1
        )

        stdout_iter = iter(stdout.readline, '')
        stderr_iter = iter(stderr.readline, '')

        for out, err in zip_longest(stdout_iter, stderr_iter):
            if out:
                sys.stdout.write(out)
            if err:
                sys.stderr.write(err)

        return stdin, stdout, stderr

    def pull(self: paramiko.SSHClient, remote_path, local_path):
        with self.open_sftp() as sftp:
            size = sftp.lstat(remote_path).st_size
            with click.progressbar(label='scp pull backup', length=size, show_pos=True) as bar:
                def cb(a, b):
                    bar.update(a - cb.pre)
                    cb.pre = a
                cb.pre = 0
                sftp.get(remote_path, local_path, cb)
    def push(self, local_path, remote_path):
        with self.open_sftp() as sftp:
            size = os.lstat(local_path).st_size
            with click.progressbar(label='scp pull backup', length=size, show_pos=True) as bar:
                def cb(a, b):
                    bar.update(a - cb.pre)
                    cb.pre = a
                cb.pre = 0
                sftp.put(local_path, remote_path, cb)