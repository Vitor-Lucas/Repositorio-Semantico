import datetime
import sys
import time

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from playwright.sync_api import sync_playwright
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib.request
from enum import Enum
import pandas as pd
import requests
import psutil
import utils
from utils import print_mid_warning, print_serious_warning, print_info, print_green, print_delimiter, color_status_code
import os
import re


def download_file(url: str, file_path: str):
    response = requests.get(url)

    if response.status_code == 200:
        try:
            urllib.request.urlretrieve(url, file_path)
            print_green(f"✅ PDF baixado com urllib: {file_path}", bright=True)
        except Exception as e:
            print_serious_warning(f"❌ Erro ao baixar o PDF: {e}")


class ICADownloadMode(Enum):
    ActiveICAS = 1
    AllICAS = 2


class ICAExtrator:
    def __init__(self, icas_dataframe_path: str, icas_download_dir: str):
        self.icas_dataframe_path = icas_dataframe_path
        self.icas_download_dir = icas_download_dir

    def create_ica_dataframe(self):
        print_delimiter(40)
        print("INICIANDO PROCESSO DE OBTENÇÃO DOS ICAS")

        df_schema = self.get_all_active_icas()

        print('Estrutura do dataframe criado!')
        print(f'Quantidade de linhas no dataframe: {len(df_schema["numero"])}')
        dataframe = pd.DataFrame(df_schema)
        dataframe.to_csv(self.icas_dataframe_path, index=False)
        print(f'Dataframe criado no caminho "{self.icas_dataframe_path}"')
        print_delimiter(40)

    def get_all_icas(self, verbose: bool = True):
        print_delimiter(40)
        print_green('INICIAÇÃO DO PROCESSO DE BUSCA POR ICAS REVOGADOS OU VIGENTES')

        url = r"https://publicacoes.decea.mil.br/pesquisa?q=ICA"
        html_content = get_html_from_url(url, verbose=verbose)
        soup = BeautifulSoup(html_content, 'html.parser')

        ica_cards = soup.find_all(
            'div', {'class': 'MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation1 '
                             'MuiCard-root mui-gpdbs6'}
        )

        ica_informations = []
        for ica_card in ica_cards:
            ica_number = ica_card.find('h5').get_text()

            texts = []
            # vigor, vazio, texto com revogação, Categoria, "Detalhes"
            for div in ica_card.find_all('div'):
                if div.find('div'):
                    continue
                texts.append(div.get_text())

            # link = ica_card.find('a').get('href')
            # print(f"Link do ICA: {link}")

            data_vigor = texts[0][-10:]
            revogado = False
            if not is_date(data_vigor):
                if verbose:
                    print('ICA REVOGADO!!!!')
                revogado = True
                data_vigor = ""
            descricao = texts[2]
            categoria = texts[3]

            resultado_revogacao = re.search(r'Revog.*', descricao, re.IGNORECASE | re.DOTALL)
            if resultado_revogacao:
                resultado_ica_revogado = re.search(r'ICA.*', resultado_revogacao.group(), re.IGNORECASE | re.DOTALL)
                if resultado_ica_revogado and verbose:
                    print(f"ESSE ICA REVOGA: {resultado_ica_revogado.group()}")
                    # TODO explorar o que eu posso fazer com esse código de revogação
            if verbose:
                print_delimiter(20)
                print(f'Documento analisado: {ica_number}')
                print(f'Data de vigor: {data_vigor}')
                # print(f'Descrição:\n {descricao[:40]}')
                print(f"Categoria: {categoria}")
                print('ICA salvo na memória!')
                print_delimiter(20)

            ica_informations.append([ica_number, data_vigor, categoria, revogado])

        print_delimiter(20)
        return ica_informations

    def get_all_active_icas(self):
        url = r'https://publicacoes.decea.mil.br/publicacao/indice'

        html_content = get_html_from_url(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        tbody = soup.select_one(
            'body > div:nth-of-type(5) > div > div:nth-of-type(13) > div:nth-of-type(2) > table > tbody')
        if tbody:
            print("Tabela encontrada no caminho: 'body > div:nth-of-type(5) > div > div:nth-of-type(13) > "
                  "div:nth-of-type(2) > table > tbody'")

        df_schema = {
            'numero': [],
            'titulo': [],
            'vigor_inicial': [],
            'origem': []
        }

        print('Iniciando etapa de extração das colunas da tabela')
        for tr in tbody.find_all('tr'):
            values = [element.text for element in tr.find_all(['td', 'th'])]
            numero, titulo, vigor_inicial, origem = values

            df_schema['numero'].append(numero)
            df_schema['titulo'].append(titulo)
            df_schema['vigor_inicial'].append(vigor_inicial)
            df_schema['origem'].append(origem)

        return df_schema

    def get_active_icas(self) -> list:
        with open(self.icas_dataframe_path, 'r', encoding='utf-8') as file:
            return [line.split(',') for line in file.readlines()[1:]]

    def download_ica_documents(self, mode: ICADownloadMode = ICADownloadMode.ActiveICAS):
        """
        Todos os arquivos são salvos no padrão ICA-{numero}_{data_vigor_inicio}_{data_vigor_fim}_{categoria}.pdf
        """
        print_delimiter(40)
        print_green('INICIANDO PROCESSO DE DOWNLOAD DOS ICAS', bright=True)

        print('Criando a instancia do webdriver')
        chromedriver_path = os.path.join(os.getcwd(), "ICA_Extractor", "chromedriver.exe")
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service)
        p = psutil.Process(driver.service.process.pid)
        print('Webdriver criado!')

        if mode == ICADownloadMode.ActiveICAS:
            print_green('DOWNLOAD EXCLUSIVO PARA ICAS ATIVOS', bright=True)
            icas = self.get_active_icas()
            print(f'ICAs ativos obtidos pelo caminho {self.icas_dataframe_path}')

            for numero, titulo, vigor_inicial, origem in icas[:1]:
                self.search_and_download_document(
                    numero=numero,
                    driver=driver
                )
        elif mode == ICADownloadMode.AllICAS:
            icas_list = self.get_all_icas(verbose=True)

            print_info(f'ICAs encontrados: {len(icas_list)}')

            print_green('PROCESSO INCIALIZADO PARA DOWNLOAD DE TODOS OS IGAS (REVOGADOS TAMBÉM)')
            for ica_number, data_vigor, categoria, revogado in icas_list:
                print_delimiter(20)
                print_info(f'ICA analizado: {ica_number}', bright=True)
                print_info("Informações:", bright=True)
                print_info(f'\tStatus: {"Revogado" if revogado else "Em vigência"}')
                print_info(f'\tData de inicio de vigor: {data_vigor if data_vigor else "indeterminada"}')
                print_info(f'\tCategoria: {categoria}')

                self.search_and_download_document(
                    numero=ica_number,
                    driver=driver,
                    revogado=revogado,
                    categoria=categoria,
                    inicio_vigor=data_vigor
                )

                print_delimiter(20)

        print('Fechando o driver e o processo')
        driver.close()
        p.terminate()
        print('driver e processo fechados')
        print_delimiter(40)

    def search_and_download_document(self, numero, driver, **kwargs):
        print_delimiter(20)
        numero = numero.replace(' ', '-')
        print_green(f'Inicializando download do {numero}')
        url = fr'https://publicacoes.decea.mil.br/publicacao/{numero}'
        # url = "https://publicacoes.decea.mil.br/publicacao/ICA-63-40"
        print(f'URL utilizado: {url}')

        # if not kwargs['revogado']:
        #     return

        driver.get(url)

        try:
            # Espera até que uma <table> esteja presente na página (por até 6s)
            # TODO ver se daria pra fazer ele esperar a criação de uma tabela com o xpath
            WebDriverWait(driver, 6).until(
                ec.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print_green("✅ Tabela carregada!")
            sem_tabela = False
        except Exception as e:
            print_mid_warning("⚠️ Tabela não apareceu a tempo:")
            sem_tabela = True
        # https://publicacoes.decea.mil.br/publicacao/ICA-81-4 -> exemplo de url desse tipo de arquivo
        # https://publicacoes.decea.mil.br/publicacao/ICA-63-18
        # https://publicacoes.decea.mil.br/publicacao/ICA-105-14 -> exemplo de url sem arquivo nenhum

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        # print(soup)

        # Extrai data_vigencia inicial ou final
        elemento = soup.select_one(
            "html > body > div:nth-of-type(3) > div > div:nth-of-type(1) > div > div:nth-of-type(2) > p:nth-of-type(1)"
        )

        texto_elemento = elemento.get_text()
        data_extraida = elemento.find('time').get_text().replace('/', '')  # extrai a data do texto
        data_vigencia_inicio = ""
        data_vigencia_fim = ""

        if "Revog" in texto_elemento:
            data_vigencia_fim = data_extraida
            # print(f'Data de fim de vigência: {data_vigencia_fim}')
        else:
            data_vigencia_inicio = data_extraida
            # print(f'Data de inicio de vigência: {data_vigencia_inicio}')

        elemento = soup.select_one(
            "html > body > div:nth-of-type(3) > div > div:nth-of-type(1) > div > div:nth-of-type(2) > a > p"
        )
        categoria = elemento.get_text()
        # print(f'Categoria {categoria}')
        # print(f'sem_tabela: {sem_tabela}')
        if sem_tabela:
            print_mid_warning("Tabela não encontrada, tentando baixar de outra maneira...")

            # Verifica se o botão "Visualizar" existe
            elemento = soup.select_one(
                "html > body > div:nth-of-type(3) > div > div:nth-of-type(1) > div > div:nth-of-type(3) > "
                "div:nth-of-type(1) > a"
            )
            # print(f"Elemento encontrado: {elemento}")
            if not elemento:
                print_serious_warning(
                    "Não foi possivel baixar o documento. Não existe uma forma de baixar esse arquivo pelo link "
                    "providenciado".upper())
                return

            # /html/body/div[3]/div/div[1]/div/div[3]/div[1]/a
            # /html/body/div[3]/div/div[1]/div/div[3]/div[1]/a
            # TODO Tentar fazer esse código pelo webdriver do selenium (evitar mais dependências)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url)
                time.sleep(3)
                # Espera o elemento <a> estar disponível na página
                page.wait_for_selector("xpath=/html/body/div[3]/div/div[1]/div/div[3]/div[1]/a")

                # Quando o clique abre uma nova aba/janela
                with page.expect_popup() as popup_info:
                    page.click("xpath=/html/body/div[3]/div/div[1]/div/div[3]/div[1]/a")

                popup = popup_info.value
                print("🔗 URL do arquivo:", popup.url)
                link = popup.url
                browser.close()

            file_name = "_".join([numero, data_vigencia_inicio, data_vigencia_fim, categoria]) + ".pdf"
            file_path = os.path.join(self.icas_download_dir, file_name)
            download_file(link, file_path)
        else:
            elemento = soup.select_one(
                "div:nth-of-type(3) > div > div:nth-of-type(1) > div > div:nth-of-type(5) > div > table")

            for tr in elemento.find_all('tr'):
                all_td = tr.find_all('td')

                for td in all_td:
                    if td.find('a'):  # pega o link do documento
                        link = td.find('a').get('href')
                        print(f"Link do documento: {link}")
                        file_name = "_".join([numero, data_vigencia_inicio, data_vigencia_fim, categoria]) + ".pdf"
                        file_path = os.path.join(self.icas_download_dir, file_name)
                        # download_file(link, file_path)
                    # print(f'{td.getText()}', end='| ')
                # print()
        # print_delimiter(20)


def get_html_from_url(url: str, verbose: bool = True) -> str:
    response = requests.get(url)
    if verbose:
        print_info(f"URL utilizado: {url}")
        print(f"Status da requisição pra url: {color_status_code(response.status_code)}")
    html_content = response.text
    return html_content


def is_date(s: str) -> bool:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            datetime.datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    return False


if __name__ == '__main__':
    utils.garantir_cwd_para("Repositorio-Semantico")

    dataframe_path = os.path.join(os.getcwd(), "ICA_Extractor", "icas.csv")
    icas_path = os.path.join(os.getcwd(), "ICA_Extractor", "ICAS")
    extrator = ICAExtrator(
        icas_dataframe_path=dataframe_path,
        icas_download_dir=icas_path
    )

    # extrator.get_all_icas()
    # extrator.create_ica_dataframe()
    # download_mode = ICADownloadMode.ActiveICAS
    download_mode = ICADownloadMode.AllICAS
    extrator.download_ica_documents(mode=download_mode)
