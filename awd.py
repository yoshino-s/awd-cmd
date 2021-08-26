#!/usr/bin/env python3
from re import DEBUG

from paramiko import sftp
from ssh import SSHClient
from typing import Optional
import click
import paramiko
import subprocess

client: SSHClient


@click.group()
@click.option('-i', '--ip', help='ip to connect to', required=True)
@click.option('-p', '--port', help='port to connect to', default=22)
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-P', '--password', help='password to use', required=True)
def awd(ip: str, port: int, user: str, password: str):
    global client, sftp
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, port=port, username=user, password=password)


@awd.command()
def interactive():
    """Runs the interactive shell"""
    client.open_shell()


@awd.command("push")
@click.argument('local_path', type=click.Path(exists=True))
@click.argument('remote_path', type=click.Path())
def push_file(local_path: str, remote_path: str):
    """push a file to the remote server"""
    client.push(local_path, remote_path)

@awd.command("pull")
@click.argument('remote_path', type=click.Path())
@click.argument('local_path', type=click.Path(exists=True))
def pull_file(local_path: str, remote_path: str):
    """push a file to the remote server"""
    client.pull(local_path, remote_path)


@awd.group(invoke_without_command=True)
@click.pass_context
def backup(ctx):
    """backup files"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(html)


@backup.command()
def html():
    """Backup the html files"""
    client.run('cd /tmp && tar -cvf backup.tar.gz /var/www/html')
    client.pull('/tmp/backup.tar.gz', 'backup.tar.gz')


@backup.command()
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-p', '--password', help='password to use', default='root')
@click.option('-d', '--database', help='database to backup', default='awd')
def db(user, password, database):
    """Backup the database"""
    client.run(
        f'cd /tmp && mysqldump {database} -u{user} -p{password} > backup.sql')
    client.pull(f'/tmp/backup.sql', 'backup.sql')


@awd.group(invoke_without_command=True)
@click.pass_context
def recovery(ctx):
    """recovery files"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(html_recovery)


@recovery.command("html")
def html_recovery():
    """Recover the html files"""
    client.run(
        f'cd /tmp && tar -xvf backup.tar.gz && rm -rf /var/www/html/* && cp -r /tmp/var/www/html/* /var/www/html/ && chmod -R 777 /var/www/html/')


@recovery.command("db")
@click.option('-u', '--user', help='user to connect as', default='root')
@click.option('-p', '--password', help='password to use', default='root')
@click.option('-d', '--database', help='database to backup', default='awd')
def db_recovery(user, password, database):
    """Backup the database"""
    sftp = client.open_sftp()
    client.run(f"mysql -u{user} -p{user} -e 'create database if not exists {database}'")
    client.run(
        f'cd /tmp && mysql {database} -u{user} -p{password} < backup.sql')


@awd.group(invoke_without_command=True)
@click.pass_context
def waf(ctx):
    """add waf"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(push)


@waf.command()
def push():
    """Push the waf files"""
    subprocess.check_call(['tar', '-cvf', 'waf.tar.gz', 'waf'])
    client.push(f'waf.tar.gz', '/tmp/waf.tar.gz')
    client.run(f'cd /tmp && tar -xvf waf.tar.gz && mkdir -p /tmp/waf/log/ && chmod -R 777 /tmp/waf/log')

@waf.command()
def log():
    client.run('cd /tmp/waf && tar -cvf log.tar.gz log')
    client.pull(f'/tmp/waf/log.tar.gz', 'log.tar.gz')
    subprocess.check_call(['tar', '-xvf', 'log.tar.gz'])


@waf.command()
@click.option('-p', '--password', default='birdwatch')
@click.argument('action', type=click.Choice(['install', 'uninstall']))
def watchbird(password, action: str):
    """manage watchbird"""
    if action == 'install':
        client.run(
            'sed -i \'s|birdwatch|'+password+'|\' /tmp/waf/watchbird.php')
        client.run('php /tmp/waf/watchbird.php --install /var/www/html')
    else:
        client.run('php /tmp/waf/watchbird.php --uninstall /var/www/html')


@waf.command()
@click.option('-l', '--log', default='/tmp/waf/log/log-{time}.log')
@click.argument('action', type=click.Choice(['install', 'uninstall']))
def intercept(action, log):
    """manage intercept"""
    if action == 'install':
        client.run(
            'sed -i \'s|/tmp/log-{time}\\.log|'+log+'|\' /tmp/waf/intercept.php')
        client.run('php /tmp/waf/waf.php install /var/www/html/ /tmp/waf/intercept.php')
    else:
        client.run(
            'php /tmp/waf/waf.php uninstall /var/www/html/ /tmp/waf/intercept.php')


if __name__ == '__main__':
    awd()
