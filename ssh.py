import termios
import click
import paramiko
import sys
import os
import select
import socket
import tty
from itertools import zip_longest


class SSHClient(paramiko.SSHClient):
    def open_shell(self: paramiko.SSHClient, start_up = None):
        # save current tty settings
        oldtty = termios.tcgetattr(sys.stdin)

        channel = self.invoke_shell()

        def resize_pty():
            size = os.get_terminal_size()
            tty_height, tty_width = size.lines, size.columns

            try:
                channel.resize_pty(width=int(tty_width),
                                   height=int(tty_height))
            except paramiko.SSHException:
                pass
        if start_up:
            channel.send(start_up)
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
            # restore old tty settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

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
            with click.progressbar(label='scp pull', length=size, show_pos=True) as bar:
                def cb(a, b):
                    bar.update(a - cb.pre)
                    cb.pre = a
                cb.pre = 0
                sftp.get(remote_path, local_path, cb)

    def push(self, local_path, remote_path):
        with self.open_sftp() as sftp:
            size = os.lstat(local_path).st_size
            with click.progressbar(label='scp push', length=size, show_pos=True) as bar:
                def cb(a, b):
                    bar.update(a - cb.pre)
                    cb.pre = a
                cb.pre = 0
                sftp.put(local_path, remote_path, cb)
