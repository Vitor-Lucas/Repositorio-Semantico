import os
from colorama import Fore, Style, init


def garantir_cwd_para(pasta_alvo):
    """
    Sobe diretórios até encontrar a pasta alvo e define o cwd nela.
    """
    caminho_atual = os.getcwd()

    while True:
        # Caminho potencial
        candidato = os.path.join(caminho_atual, pasta_alvo)
        if os.path.isdir(candidato):
            os.chdir(candidato)
            print(f"✅ CWD alterado para: {os.getcwd()}")
            return

        # Sobe um nível
        novo = os.path.dirname(caminho_atual)
        if novo == caminho_atual:
            break  # chegou na raiz
        caminho_atual = novo

    print(f"⚠️ Pasta '{pasta_alvo}' não encontrada em nenhum nível acima.")


def print_serious_warning(message: str):
    print(Style.BRIGHT + Fore.RED + message + '\033[0m')


def print_mid_warning(message: str):
    print(Fore.RED + message + '\033[0m')


def print_info(message: str, bright: bool = False):
    print(Fore.BLUE + (Style.BRIGHT if bright else "") + message + '\033[0m')


def print_green(message: str, bright: bool = False):
    print(Fore.GREEN + (Style.BRIGHT if bright else "") + message + '\033[0m')


def print_cyan(message: str, bright: bool = False):
    print(Fore.CYAN + (Style.BRIGHT if bright else "") + message + '\033[0m')


def print_delimiter(length: int = 40, delimiter: str = '-'):
    print_cyan(delimiter * length)


def color_status_code(status_code: int):
    if status_code == 200:
        color = Fore.GREEN
    elif status_code == 404:
        color = Fore.RED
    else:
        color = Fore.YELLOW
    return color + Style.BRIGHT + f"{status_code}"
