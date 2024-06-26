#!/usr/bin/env python3
"""Import mssl Data"""
import click
from application import app, logger
from application.models.host import Host
from application.helpers.get_account import get_account_by_name
from application.modules.debug import ColorCodes
from application.helpers.cron import register_cronjob
try:
    import pypyodbc as pyodbc
    import sqlserverport
except ImportError:
    logger.debug("Info: Mssql Plugin was not able to load required modules")

@app.cli.group(name='mssql')
def cli_mssql():
    """Mssql Related commands"""

def mssql_import(account):
    """
    Mssql Import
    """
    try:
        config = get_account_by_name(account)

        print(f"{ColorCodes.OKBLUE}Started {ColorCodes.ENDC} with account "\
              f"{ColorCodes.UNDERLINE}{config['name']}{ColorCodes.ENDC}")

        serverport = sqlserverport.lookup(config['address'], config['instance'])
        server = f'{config["address"]},{serverport}'
        connect_str = f'DRIVER={{{config["driver"]}}};SERVER={server};'\
                      f'DATABASE={config["database"]};UID={config["username"]};'\
                      f'PWD={config["password"]};TrustServerCertificate=YES'
        logger.debug(connect_str)
        cnxn = pyodbc.connect(connect_str)
        cursor = cnxn.cursor()
        query = f"select {config['fields']} from {config['table']};"
        if "custom_query" in config:
            query = config['custom_query']
        logger.debug(query)
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            labels=dict(zip(config['fields'].split(","),row))
            hostname = labels[config['hostname_field']].strip().lower()
            if 'rewrite_hostname' in config and config['rewrite_hostname']:
                hostname = Host.rewrite_hostname(hostname, config['rewrite_hostname'], labels)
            print(f" {ColorCodes.OKGREEN}* {ColorCodes.ENDC} Check {hostname}")
            del labels[config['hostname_field']]
            host_obj = Host.get_host(hostname)
            host_obj.update_host(labels)
            do_save=host_obj.set_account(account_dict=config)
            if do_save:
                host_obj.save()
            else:
                print(f" {ColorCodes.WARNING} * {ColorCodes.ENDC} Managed by diffrent master")
    except NameError as error:
        print(f"EXCEPTION: Missing requirements, pypyodbc or sqlserverport ({error})")

@cli_mssql.command('import_hosts')
@click.argument('account')
def cli_mssql_import(account):
    """Import MSSQL Hosts"""
    mssql_import(account)

register_cronjob("MSSql: Import Hosts", mssql_import)
