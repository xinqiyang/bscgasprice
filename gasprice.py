import os
import click
import logging
import pandas as pd
from time import sleep
from threading import Thread
from collections import deque
from statistics import mean
from itertools import chain
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from sanic import Sanic, response
from retry import retry
import random

# https://bsc-dataseed1.defibit.io/
# https://bsc-dataseed1.ninicoin.io/  # is to slow
BSC_RPCS = ['https://bsc-dataseed.binance.org/', 'https://bsc-dataseed1.defibit.io/']
BSC_RPC_URL = os.environ.get('BSC_RPC_URL', BSC_RPCS[0])

QUANTILES = dict(SafeGasPrice=0, ProposeGasPrice=5, FastGasPrice=7.5, InstantGasPrice=15)
WINDOW = 50


w3 = Web3(HTTPProvider(BSC_RPC_URL, request_kwargs={'timeout': 5}))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
app = Sanic('bscgas')
log = logging.getLogger('sanic.error')
app.config.LOGO = ''
block_times = deque(maxlen=WINDOW)
blocks_gwei = deque(maxlen=WINDOW)
stats = {}

instances = {}

def web3_instance():  
    random_index = random.randint(0, len(BSC_RPCS)-1)
    w3 = Web3(HTTPProvider(BSC_RPCS[random_index],request_kwargs={'timeout': 5}))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0, name='i'+str(random_index))
    # print("get index ----:", random_index)
    return w3
    

# @retry(Exception, delay=2, logger=log)
def worker(skip_warmup):
    stats['health'] = False
    localw3 = web3_instance()
    localw3.middleware_onion.inject(geth_poa_middleware, layer=0)
    # print(localw3.clientVersion)
    latest = localw3.eth.filter('latest')
    # print('worker:', latest)
    if not skip_warmup and not block_times:
        warmup()
    
    while True:
        try:
            for n in latest.get_new_entries():
                process_block(localw3, n)
                log.info(str(stats))
            if not localw3.eth.syncing:
                stats['health'] = True
        except:
            sleep(5)
            localw3 = web3_instance()
            latest = localw3.eth.filter('latest')
            # print("do reconnect -------", localw3, latest)
            continue
        sleep(2)


def warmup():
    tip = w3.eth.blockNumber
    with click.progressbar(range(tip - WINDOW, tip), label='warming up') as bar:
        for n in bar:
            process_block(w3, n)


def block_time():
    if len(block_times) < 2:
        return 0
    times = sorted(block_times)
    avg = mean(b - a for a, b in zip(times, times[1:]))
    stats['block_time'] = round(avg, 2)
    return avg

def average(lst):
    return sum(lst) / len(lst)

def process_block(w3i, n):
    block = w3i.eth.getBlock(n, True)
    stats['block_number'] = block.number

    block_times.append(block.timestamp)
    if len(block_times) > 1:
        t = sorted(block_times)
        stats['block_time'] = round(mean(b - a for a, b in zip(t, t[1:])), 3)

    if block.transactions:
        prices = []
        for tx in block.transactions:
            if int(tx.gasPrice) > 0:
                prices.append(tx.gasPrice)
        blocks_gwei.append(min(prices))
        data = pd.Series(blocks_gwei)
        for name, q in QUANTILES.items():
            if name in ['FastGasPrice']:
                stats[name] = round(float(w3i.fromWei(average(prices), 'gwei')), 3)
            elif name in ['InstantGasPrice']:
                stats[name] = round(float(w3i.fromWei(max(prices), 'gwei')), 3)
            else:
                price = data.quantile(q / 100)
                stats[name] = round(float(w3i.fromWei(price, 'gwei')), 3)
    print(stats)
    return block


@app.route('/')
async def api(request):
    return response.json(stats)


@app.route('/health')
async def health(request):
    return response.json({'health': stats['health']}, status=200 if stats['health'] else 503)


@click.command()
@click.option('--host', '-h', default='0.0.0.0')
@click.option('--port', '-p', default=8000)
@click.option('--skip-warmup', '-s', is_flag=False)
def main(host, port, skip_warmup):
    print('skip_warmup', skip_warmup, host, port)
    bg = Thread(target=worker, args=(skip_warmup,))
    bg.daemon = True
    bg.start()
    app.run(host=host, port=port, access_log=False)


if __name__ == '__main__':
    main()
