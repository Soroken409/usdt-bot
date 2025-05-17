import requests
from telegram import Bot
from telegram.utils.request import Request
import time
from datetime import datetime, timedelta
import json
import os

TELEGRAM_TOKEN = '8187750918:AAGfLkmF63TdCnuG4HuWDN--M-ByNPCHZ8w'
BSC_API_KEY = 'Z9MEX2PVK76FT6BY2IG8E8ZE7XXZ49BE6I'
BALANCE_FILE = 'balances.json'

request = Request(con_pool_size=8, read_timeout=10)
bot = Bot(token=TELEGRAM_TOKEN, request=request)

wallets = {
    'Назар': '0x064159d17Edfc9dF0DD88D790c71FecfFD934402',
    'Смайлик': '0xbDfb0f9fCbE22AB6ea0E51CcaC099B84B9B7aDa5',
    'Єма': '0xF830F0D9Ac3294af0856DE977723842A15e5db78',
    'Томах': '0xe40a836da658F146FA3bf4DcD2f0cE30dB78ec43',
    'Остап': '0xC0478E636dCC49204aFc3dE81D5D7A2f87960b55',
    'Елла': '0xD3d74e251aFE9Faec27aF8d8F64a06734f7d1Dac',
    'Мама': '0x2c04012a323c98Ee4037370C8198394041718754',
    'Тато': '0x31e1dD35F0cc3dAc7c7bCFc80521Ba871c78aE5b',
    'Олег': '0xd44449843FEF24c72ca0E171b52607933B47A29e',
}

USDT_CONTRACT = '0x55d398326f99059fF775485246999027B3197955'
BNB_CONTRACT = None

def get_token_balance(wallet, token_contract=None):
    if token_contract:
        url = f'https://api.bscscan.com/api?module=account&action=tokenbalance&contractaddress={token_contract}&address={wallet}&tag=latest&apikey={BSC_API_KEY}'
    else:
        url = f'https://api.bscscan.com/api?module=account&action=balance&address={wallet}&tag=latest&apikey={BSC_API_KEY}'
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        raw_balance = int(data['result'])
        return raw_balance / 1e18
    except:
        return 0

def load_balances():
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_balances(balances):
    with open(BALANCE_FILE, 'w') as f:
        json.dump(balances, f, indent=2)

def save_daily_balances():
    today = datetime.now().strftime('%Y-%m-%d')
    balances = load_balances()
    balances[today] = {}

    for name, address in wallets.items():
        usdt = get_token_balance(address, USDT_CONTRACT)
        bnb = get_token_balance(address, BNB_CONTRACT)
        balances[today][name] = {
            "USDT": round(usdt, 2),
            "BNB": round(bnb, 6)
        }

    save_balances(balances)

def check_swaps(address):
    url = (
        f'https://api.bscscan.com/api?module=account&action=txlist'
        f'&address={address}&startblock=0&endblock=99999999'
        f'&sort=desc&apikey={BSC_API_KEY}'
    )
    try:
        response = requests.get(url, timeout=10)
        txs = response.json().get("result", [])
        start_of_day = datetime.combine(datetime.now().date(), datetime.min.time()).timestamp()

        for tx in txs:
            if int(tx["timeStamp"]) < start_of_day:
                break
            if int(tx["isError"]) == 0:
                return True
    except:
        pass
    return False

def format_balance_report():
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    balances = load_balances()
    report = f'🕒 Звіт на {now.strftime("%Y-%m-%d %H:%M")}\n\n'

    for name, address in wallets.items():
        usdt = get_token_balance(address, USDT_CONTRACT)
        bnb = get_token_balance(address, BNB_CONTRACT)

        report += f'{name} - {address}\n\n'
        report += f'{usdt:.2f} USDT'
        if yesterday in balances and name in balances[yesterday]:
            diff_usdt = usdt - balances[yesterday][name]['USDT']
            report += f' (витрати за {yesterday}: {diff_usdt:+.2f} USDT)'
        report += '\n'

        report += f'{bnb:.6f} BNB'
        if yesterday in balances and name in balances[yesterday]:
            diff_bnb = bnb - balances[yesterday][name]['BNB']
            report += f' (витрати за {yesterday}: {diff_bnb:+.6f} BNB)'
        report += '\n'

        if check_swaps(address):
            report += f'Своп виконано ✅\n'
        else:
            report += f'Своп ще не виконувався ❌\n'

        report += f'[Перевірити](https://bscscan.com/address/{address.lower()})\n\n'

    return report.strip()

def main_loop(chat_id):
    print("✅ Бот запущено, чекає на 55 хвилину...")
    while True:
        now = datetime.now()

        if now.hour == 23 and now.minute == 55:
            save_daily_balances()
            bot.send_message(chat_id=chat_id, text='📀 Баланси збережено на 23:55')
            time.sleep(60)
            continue

        if now.minute == 55:
            report = format_balance_report()
            bot.send_message(chat_id=chat_id, text=report, parse_mode="Markdown")
            time.sleep(60)
            continue

        time.sleep(15)

if __name__ == '__main__':
    updates = bot.get_updates()
    if updates:
        chat_id = updates[-1].message.chat_id
        main_loop(chat_id)
    else:
        print("❗️ Напиши щось боту в Telegram, щоб отримати chat_id.")
