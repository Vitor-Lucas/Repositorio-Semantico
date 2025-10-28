import datetime

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib.request
import pandas as pd
import requests
import psutil
import utils
import os
import re


def download_file(url: str, file_path: str):
    response = requests.get(url)

    if response.status_code == 200:
        try:
            urllib.request.urlretrieve(url, file_path)
            print(f"✅ PDF baixado com urllib: {file_path}")
        except Exception as e:
            print(f"❌ Erro ao baixar o PDF: {e}")


class ICAExtrator:
    def __init__(self, icas_dataframe_path: str, icas_download_dir: str):
        self.icas_dataframe_path = icas_dataframe_path
        self.icas_download_dir = icas_download_dir

    def create_ica_dataframe(self):
        print('-' * 40)
        print("INICIANDO PROCESSO DE OBTENÇÃO DOS ICAS")

        df_schema = self.get_all_active_icas()

        print('Estrutura do dataframe criado!')
        print(f'Quantidade de linhas no dataframe: {len(df_schema["numero"])}')
        dataframe = pd.DataFrame(df_schema)
        dataframe.to_csv(self.icas_dataframe_path, index=False)
        print(f'Dataframe criado no caminho "{self.icas_dataframe_path}"')
        print('-' * 40)

    def get_all_icas(self):
        print('-'*40)
        print('INICIAÇÃO DO PROCESSO DE BUSCA POR ICAS REVOGADOS OU VIGENTES')

        url = r"https://publicacoes.decea.mil.br/pesquisa?q=ICA"
        html_content = get_html_from_url(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        ica_cards = soup.find_all(
            'div', {'class': 'MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation1 '
                             'MuiCard-root mui-gpdbs6'}
        )

        ica_informations = []
        for ica_card in ica_cards:
            print('-'*20)
            ica_number = ica_card.find('h5').get_text()
            print(f'Documento analisado: {ica_number}')

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
                print('ICA REVOGADO!!!!')
                revogado = True
                data_vigor = ""
            descricao = texts[2]
            categoria = texts[3]

            resultado_revogacao = re.search(r'Revog.*', descricao, re.IGNORECASE | re.DOTALL)
            if resultado_revogacao:
                resultado_ica_revogado = re.search(r'ICA.*', resultado_revogacao.group(), re.IGNORECASE | re.DOTALL)
                if resultado_ica_revogado:
                    print(f"ESSE ICA REVOGA: {resultado_ica_revogado.group()}")

            print(f'Data de vigor: {data_vigor}')
            # print(f'Descrição:\n {descricao[:40]}')
            print(f"Categoria: {categoria}")

            ica_informations.append([ica_number, data_vigor, categoria, revogado])
            print('ICA salvo na memória!')
            print('-'*20)

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

    def download_ica_documents(self):
        """
        Todos os arquivos são salvos no padrão ICA-{numero}_{data_vigor_inicio}_{data_vigor_fim}.pdf
        """
        print('-' * 40)
        print('INICIANDO PROCESSO DE DOWNLOAD DOS ICAS')
        icas = self.get_active_icas()
        print(f'ICAs ativos obtidos pelo caminho {self.icas_dataframe_path}')

        print('Criando a instancia do webdriver')
        # chromedriver_path = r"C:\Users\vitor\Downloads\chromedriver_win32\chromedriver.exe"
        chromedriver_path = os.path.join(os.getcwd(), "ICA_Extractor", "chromedriver.exe")
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service)
        p = psutil.Process(driver.service.process.pid)
        print('Webdriver criado!')

        for numero, titulo, vigor_inicial, origem in icas[:1]:
            print('-' * 20)
            numero = numero.replace(' ', '-')
            print(f'Inicializando download do {numero}')
            url = fr'https://publicacoes.decea.mil.br/publicacao/{numero}'
            print(f'URL utilizado: {url}')
            driver.get(url)

            try:
                # Espera até que uma <table> esteja presente na página (por até 15s)
                WebDriverWait(driver, 15).until(
                    ec.presence_of_element_located((By.TAG_NAME, "table"))
                )
                print("✅ Tabela carregada!")
            except Exception as e:
                print("⚠️ Tabela não apareceu a tempo:", e)

            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            # print(soup)
            elemento = soup.select_one(
                "div:nth-of-type(3) > div > div:nth-of-type(1) > div > div:nth-of-type(5) > div > table")
            # elemento = soup.find('table')
            # print(elemento)
            # TODO fazer um sistema que analisa todas as linhas dessa tabela e pega a unica que está em vigencia.
            for tr in elemento.find_all('tr'):
                all_td = tr.find_all('td')
                data_vigor_inicio = ""
                data_vigor_fim = ""

                if all_td:  # se a linha não está vazia
                    # print([a.get_text() for a in all_td])
                    data_vigor_inicio = all_td[2].get_text().replace('/', '')
                    data_vigor_fim = all_td[3].get_text().replace('/', '')
                    print(f'ICA entrou em vigor na data: {data_vigor_inicio}')

                for td in all_td:
                    if td.find('a'):  # pega o link do documento
                        link = td.find('a').get('href')
                        print(f"Link do documento: {link}")
                        file_name = "_".join([numero, data_vigor_inicio, data_vigor_fim]) + ".pdf"
                        file_path = os.path.join(self.icas_download_dir, file_name)
                        download_file(link, file_path)
                    # print(f'{td.getText()}', end='| ')
                print()
            print('-' * 20)

        print('Fechando o driver e o processo')
        driver.close()
        p.terminate()
        print('driver e processo fechados')
        print('-' * 40)


def get_html_from_url(url: str) -> str:
    print(f"URL utilizado: {url}")
    response = requests.get(url)
    print(f"Status da requisição pra url: {response.status_code}")
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

    extrator.get_all_icas()
    # extrator.create_ica_dataframe()
    # extrator.download_ica_documents()
