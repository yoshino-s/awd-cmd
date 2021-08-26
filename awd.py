#!/usr/bin/env python3
from os import unlink

from tabulate import tabulate
import csv
from ssh import SSHClient
from typing import List
import click
import paramiko
import subprocess
import os
from datetime import datetime
from os.path import join

client: SSHClient
base = "data/"
directory: str = "default/"
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")


@click.group()
@click.option('-i', '--ip', help='ip to connect to', required=True)
@click.option('-p', '--port', help='port to connect to', default=22)
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-P', '--password', help='password to use', required=True)
def awd(ip: str, port: int, user: str, password: str):
    global client, directory
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, port=port, username=user, password=password)
    directory = f"{user}_{ip}_{port}/"
    directory = os.path.join(base, directory)
    os.makedirs(directory, exist_ok=True)


@awd.command("interactive")
@click.argument('cmd', default="exec bash; cd /var/www/html")
def interactive(cmd):
    """Runs the interactive shell"""
    client.open_shell(cmd+"\n")


@awd.command("push")
@click.argument('local_path', type=click.Path(exists=True))
@click.argument('remote_path', type=click.Path())
def push(local_path: str, remote_path: str):
    """push a file to the remote server"""
    client.push(local_path, remote_path)


@awd.command("pull")
@click.argument('remote_path', type=click.Path())
@click.argument('local_path', type=click.Path(exists=True))
def pull(local_path: str, remote_path: str):
    """push a file to the remote server"""
    client.pull(local_path, remote_path)


@awd.group(invoke_without_command=True)
@click.pass_context
def backup(ctx):
    """backup files"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(backup_html)


@backup.command("html")
def backup_html():
    """Backup the html files"""
    name = timestamp + "-backup.tar.gz"
    client.run(f'cd /tmp; tar -cvf backup.tar.gz /var/www/html; cp backup.tar.gz {name}')
    client.pull(f'/tmp/{name}', join(directory, name))


@backup.command("db")
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-p', '--password', help='password to use', default='root')
@click.option('-d', '--database', help='database to backup', default='awd')
def backup_db(user, password, database):
    """Backup the database"""
    name = timestamp + "-backup.sql"
    client.run(
        f'cd /tmp; mysqldump {database} -u{user} -p{password} > backup.sql; cp backup.sql {name}')
    client.pull(f'/tmp/{name}', join(directory, name))


@awd.group(invoke_without_command=True)
@click.pass_context
def recovery(ctx):
    """recovery files"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(recovery_html)


@recovery.command("html")
def recovery_html():
    """Recover the html files"""
    client.run(
        f'cd /tmp; tar -xvf backup.tar.gz; rm -rf /var/www/html/*; cp -r /tmp/var/www/html/* /var/www/html/; chmod -R 777 /var/www/html/')


@recovery.command("db")
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-p', '--password', help='password to use', default='root')
@click.option('-d', '--database', help='database to backup', default='awd')
def recovery_db(user, password, database):
    """Backup the database"""
    sftp = client.open_sftp()
    client.run(
        f"mysql -u{user} -p{user} -e 'create database if not exists {database}'")
    client.run(
        f'cd /tmp; mysql {database} -u{user} -p{password} < backup.sql')


@awd.group(invoke_without_command=True)
@click.pass_context
def waf(ctx):
    """add waf"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(waf_push)


@waf.command("push")
def waf_push():
    """Push the waf files"""
    subprocess.check_call(['tar', '-cvf', 'waf.tar.gz', 'waf'])
    client.push(f'waf.tar.gz', '/tmp/waf.tar.gz')
    client.run(
        f'cd /tmp; tar -xvf waf.tar.gz; mkdir -p /tmp/waf/log/; chmod -R 777 /tmp/waf/log')


@waf.command("log")
def waf_log():
    name = join(directory, 'log.tar.gz')
    client.run('cd /tmp/waf; tar -cvf log.tar.gz log')
    client.pull(f'/tmp/waf/log.tar.gz', name)
    subprocess.check_call(['tar', '-xf', 'log.tar.gz'], cwd=directory)
    unlink(name)


@waf.command("watchbird")
@click.option('-p', '--password', default='birdwatch')
@click.argument('action', type=click.Choice(['install', 'uninstall']))
def waf_watchbird(password, action: str):
    """manage watchbird"""
    if action == 'install':
        client.run(
            'sed -i \'s|birdwatch|'+password+'|\' /tmp/waf/watchbird.php')
        client.run('php /tmp/waf/watchbird.php --install /var/www/html')
    else:
        client.run('php /tmp/waf/watchbird.php --uninstall /var/www/html')


@waf.command("intercept")
@click.option('-l', '--log', default='/tmp/waf/log/log-{time}.log')
@click.argument('action', type=click.Choice(['install', 'uninstall']))
def waf_intercept(action, log):
    """manage intercept"""
    if action == 'install':
        client.run(
            'sed -i \'s|/tmp/log-{time}\\.log|'+log+'|\' /tmp/waf/intercept.php')
        client.run(
            'php /tmp/waf/waf.php install /var/www/html/ /tmp/waf/intercept.php')
    else:
        client.run(
            'php /tmp/waf/waf.php uninstall /var/www/html/ /tmp/waf/intercept.php')


@awd.group()
def python():
    """python utils"""
    pass


@python.command("push")
def python_push():
    client.push("cpython.tar.gz", "/tmp/cpython.tar.gz")
    client.run("cd /tmp; tar -xvf cpython.tar.gz")


@python.command("run")
def python_run():
    client.open_shell("/tmp/cpython/python\n")


@python.command("watch")
def python_watch():
    client.push("monitor/watch.py", "/tmp/watch.py")
    client.open_shell(
        "cd /var/www/html; /tmp/cpython/python /tmp/watch.py\n")


@awd.group()
def hm():
    """hm utils"""
    pass


@hm.command("push")
def hm_push():
    client.push("hm.tar.gz", "/tmp/hm.tar.gz")
    client.run("cd /tmp; tar -xvf hm.tar.gz")


@hm.command("run")
@click.argument('args', nargs=-1)
def hm_run(args: List[str]):
    client.run(f"/tmp/hm/hm {' '.join(args)}")


@hm.command("scan")
def hm_scan():
    client.run("/tmp/hm/hm scan /var/www/html")
    client.pull("/tmp/hm/result.csv", "result.csv")
    with open('result.csv') as inf:
        reader = csv.reader(inf)
        print(tabulate(reader, headers="firstrow"))
    unlink("result.csv")


@hm.command("deepscan")
def hm_deepscan():
    name = timestamp + "-hm_result.csv"
    p = join(directory, name)
    client.run("/tmp/hm/hm deepscan /var/www/html")
    client.pull("/tmp/hm/result.csv", p)
    with open(p) as inf:
        reader = csv.reader(inf)
        print(tabulate(reader, headers="firstrow"))


if __name__ == '__main__':
    awd()
