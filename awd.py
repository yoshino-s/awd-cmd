#!/usr/bin/env python3
import logging
from verboselogs import VerboseLogger
from glob import glob
import json
from os import unlink
import sys
import time

from tabulate import tabulate
import csv
from core.process import process_record
from ssh import SSHClient
from typing import Any, Dict, List
import click
import paramiko
import os
import tarfile
from datetime import datetime
from os.path import join
import yaml
import coloredlogs

coloredlogs.install()

logger = VerboseLogger(__name__)

logging.getLogger("paramiko").setLevel(logging.WARN)

client: SSHClient
base = "data/"
directory: str = "default/"
machine = ""
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")


config: Dict[str, Any] = {}

if os.path.exists("./config.yml"):
    with open("./config.yml") as f:
        config = yaml.safe_load(f)


@click.group(invoke_without_command=True)
@click.option('-t', '--target', help='target to connect to')
@click.option('-i', '--ip', help='ip to connect to')
@click.option('-p', '--port', help='port to connect to', default=22)
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-P', '--password', help='password to use', default="123456")
@click.pass_context
def awd(ctx, target: str, ip: str, port: int, user: str, password: str):
    global client, directory, machine
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if target:
        if not config.get(target):
            logger.error("Target not found in config")
            sys.exit(1)
        ip = config[target]["ip"]
        port = config[target].get("port", 22)
        user = config[target].get("user", "root")
        password = config[target]["password"]
    elif not ip:
        logger.error("No target or ip specified")
        sys.exit(1)

    client.connect(hostname=ip, port=port, username=user, password=password)
    directory = f"{user}_{ip}_{port}/"
    machine = f"{user}_{ip}_{port}"
    directory = os.path.join(base, directory)
    os.makedirs(directory, exist_ok=True)

    if ctx.invoked_subcommand is None:
        ctx.invoke(interactive)


@awd.command()
@click.argument('cmd', default="exec bash\ncd /var/www/html")
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
    name = timestamp + "-backup.tgz"
    local_name = join(directory, name)
    dir_name = join(directory, timestamp + "-backup")
    client.run(
        f'cd /tmp; tar -czvf backup.tgz /var/www/html; cp backup.tgz {name}')
    client.pull(f'/tmp/{name}', local_name)
    os.system(f'mkdir -p {dir_name} && tar -xzvf {local_name} -C {dir_name}')


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
@click.option("-l", "--local", help="from local", is_flag=True)
def recovery_html(local: bool):
    """Recover the html files"""
    fix_dir = join(directory, "fix")
    if local and not os.path.exists(fix_dir):
        logger.error("No fix directory found")
        sys.exit(1)
    if local:
        os.system(f"tar -czvf /tmp/fix.tgz -C {fix_dir} .")
        client.push("/tmp/fix.tgz", "/tmp/fix.tgz")
        client.run(
            "cd /var/www/html; rm -rf *; tar -xzvf /tmp/fix.tgz; chmod -R 777 /var/www/html/ && rm /tmp/fix.tgz")
    else:
        client.run(
            f'cd /tmp; tar -xzvf backup.tgz; rm -rf /var/www/html/*; cp -r /tmp/var/www/html/* /var/www/html/; chmod -R 777 /var/www/html/')


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


@awd.command()
def install():
    """
    install dependencies
    """
    client.push(f'waf.tgz', '/tmp/waf.tgz')
    client.run(
        f'cd /tmp; tar -xzvf waf.tgz; mkdir -p /tmp/waf/log/; chmod -R 777 /tmp/waf/log')

    client.push(f'attachments.tgz', '/tmp/attachments.tgz')
    client.run(
        f'cd /tmp; tar -xzvf attachments.tgz')


@awd.group()
def waf():
    pass


@waf.command("log")
def waf_log():
    name = join(directory, 'log.tgz')
    client.run('cd /tmp/waf; tar -czvf log.tgz log')
    client.pull(f'/tmp/waf/log.tgz', name)
    with tarfile.open(name, 'r:gz') as tar:
        tar.extractall(directory)
    unlink(name)


@waf.command("log_daemon")
def waf_log_daemon():
    global machine
    while True:
        logger.info("pulling log")
        name = join(directory, 'log.tgz')
        client.run('cd /tmp/waf; tar -czf log.tgz log; rm log/* -rf')
        client.pull(f'/tmp/waf/log.tgz', name)
        with tarfile.open(name, 'r:gz') as tar:
            tar.extractall(directory)
        unlink(name)
        # list all json in directory
        for name in glob(join(directory, 'log', '*.json')):
            with open(name, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    data['machine'] = machine
                    process_record(data)
            unlink(name)
        time.sleep(30)


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
def hm():
    """hm utils"""
    pass


@hm.command("run")
@click.argument('args', nargs=-1)
def hm_run(args: List[str]):
    client.run(f"/tmp/hm/hm {' '.join(args)}")


@hm.command("scan")
def hm_scan():
    name = timestamp + "-hm_result.csv"
    p = join(directory, name)
    client.run("/tmp/attachments/hema/hm scan /var/www/html")
    client.pull("/tmp/attachments/hema/result.csv", p)
    with open(p) as inf:
        reader = csv.reader(inf)
        print(tabulate(reader, headers="firstrow"))


@hm.command("deepscan")
def hm_deepscan():
    name = timestamp + "-hm_result.csv"
    p = join(directory, name)
    client.run("/tmp/attachments/hema/hm deepscan /var/www/html")
    client.pull("/tmp/attachments/hema/result.csv", p)
    with open(p) as inf:
        reader = csv.reader(inf)
        print(tabulate(reader, headers="firstrow"))


@awd.command()
@click.option("--options", help="options", default="", type=str)
def pspy(options: str):
    client.open_shell("/tmp/attachments/pspy64 " + options + "\n")


if __name__ == '__main__':
    awd()
