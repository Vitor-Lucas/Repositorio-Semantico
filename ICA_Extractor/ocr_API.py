import os
import sys

import requests
import jwt
import datetime
import json


class IloveAPI:
    # https://www.iloveapi.com/docs/api-reference
    def __init__(self):
        self.public_key = r'project_public_e075300d39d82176d7a47de3b042c42e_VLzKG82f43040a74a569ad3d44437fa3af270'
        self._private_key = r'secret_key_c13b05cc526ead59d78f9b17a0846d03_tL_7tf70ddbb5ece1b873a71296e1ed5eba2b'

    def start(self, tool: str, region: str = 'us') -> dict:
        print('-'*40)
        print('Inicialização da API')
        url = f"https://api.ilovepdf.com/v1/start/{tool}/{region}"
        print(f'URL utilizado: {url}')

        signed_token = jwt_encode(self.public_key, self._private_key)
        headers = {"Authorization": f"Bearer {signed_token}"}

        print('Realizando a requisição')
        response = requests.get(url, headers=headers)
        print(f"Status da requisição: {response.status_code}")
        print(response.content.decode('utf-8'))
        print('-'*40)
        return json.loads(response.content.decode('utf-8'))

    def upload_file(self, server: str, task_id: str, file_path: str):
        url = f"https://{server}/v1/upload"
        token = jwt_encode(self.public_key, self._private_key)
        headers = {"Authorization": f"Bearer {token}"}
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f)}
            data = {'task': task_id}
            response = requests.post(url, headers=headers, data=data, files=files)

        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.content.decode('utf-8')}")
        return json.loads(response.content.decode('utf-8'))

    def ocr_process(self, server: str, task_id: str, server_filepath: str, file_name: str):
        url = f"https://{server}/v1/process"
        token = jwt_encode(self.public_key, self._private_key)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            'task': task_id,
            'tool': 'pdfocr',
            'output_filename': f"{file_name}_ocr",
            'files': [
                {
                    'server_filename': server_filepath,
                    'filename': file_name
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload)
        print(f'Status code: {response.status_code}')
        print(f'Request contents: {response.content.decode("utf-8")}')
        print('-'*40)
        return json.loads(response.content.decode('utf-8'))

    def download_all_processed_files(self, server: str, task: str):
        url = f'https://{server}/v1/download/{task}'
        print(f'URL utilizado: {url}')
        token = jwt_encode(self.public_key, self._private_key)
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        print(f"Status code: {response.status_code}")
        # print(f'Request contents: {response.content}')
        output_path = "ICA_medio.pdf"
        if response.status_code == 200:
            # Salva o conteúdo binário em um arquivo ZIP
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Arquivo baixado com sucesso: {output_path}")
        else:
            # Caso de erro, tenta decodificar o JSON de erro (às vezes a API manda um JSON de erro)
            try:
                print(response.json())
            except Exception:
                print("❌ Erro desconhecido no download.")


def jwt_encode(public_key, private_key):
    # return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuaWxvdmVwZGYuY29tIiwiYXVkIjoiIiwiaWF0IjoxNzYxMTg0MjE5LCJuYmYiOjE3NjExODQyMTksImV4cCI6MTc2MTE4NzgxOSwianRpIjoicHJvamVjdF9wdWJsaWNfZTA3NTMwMGQzOWQ4MjE3NmQ3YTQ3ZGUzYjA0MmM0MmVfVkx6S0c4MmY0MzA0MGE3NGE1NjlhZDNkNDQ0MzdmYTNhZjI3MCJ9.B6WQnnq8UX7hD78z3q_lg7bI97iDhp52gUecObpGRNY"

    url = r"https://api.ilovepdf.com/v1/auth"
    response = requests.post(url, json={'public_key': api.public_key})
    print(response.status_code)
    print(response.content)
    return json.loads(response.content.decode('utf-8'))['token']
    # payload = {
    #     'public_key': public_key,
    #     'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    # }
    # return jwt.encode(payload, private_key, algorithm='HS256')


def get_all_paths(dir):
    """
    Retorna uma lista de tuplas (nome_arquivo, caminho_completo)
    para todos os arquivos dentro do diretório informado.
    """
    arquivos = []
    for nome in os.listdir(dir):
        caminho_completo = os.path.join(dir, nome)
        if os.path.isfile(caminho_completo):
            arquivos.append((nome, caminho_completo))
    return arquivos


if __name__ == '__main__':
    api = IloveAPI()
    response = api.start('pdfocr')

    server = response['server']
    remaining_credits = response['remaining_credits']
    task_id = response['task']

    print('INFORMAÇÔES SOBRE O PROCEDIMENTO:')
    print(f'Servidor: {server}')
    print(f'ID da Task: {task_id}')
    print(f'Créditos restantes: {remaining_credits}')
    # sys.exit()
    # files = get_all_paths(r'C:\Coding\AirData\RepositorioSemantico\ICAS')
    # files = [('ICA-96-1.pdf', r'C:\Coding\AirData\RepositorioSemantico\ICAS\ICA-96-1.pdf')]
    files = [('ICA-100-47.pdf', r'C:\Coding\AirData\RepositorioSemantico\ICAS\ICA-100-47.pdf')]
    print('-'*40)
    print('INICIALIZANDO O UPLOAD DE ARQUIVOS')
    input('Pressione qualquer botão para continuar')
    server_file_names = []
    for file_name, file_path in files:
        print('-'*30)
        print(f'Arquivo a fazer upload: {file_name}')
        response = api.upload_file(server, task_id, file_path=file_path)
        server_file_name = response['server_filename']
        print(f'Arquivo salvo com o nome: {server_file_name}')
        server_file_names.append(server_file_name)
        print('-'*30)

    print('-'*40)
    print("INICIANDO PROCESSO DE TRANSFORMAÇÃO COM OCR")
    input('Pressione qualquer botão para continuar')
    for i, (file_name, _) in enumerate(files):
        print('-'*30)
        print(f'Arquivo utilizado: {file_name}')
        response = api.ocr_process(
            server=server,
            task_id=task_id,
            server_filepath=server_file_names[i],
            file_name=file_name
        )
        print('-'*30)

    print('-' * 40)
    input('Pressione qualquer botão para continuar')
    print('INICIALIZANDO PROCESSO DE DOWLOAD DE ARQUIVOS PROCESSADOS')
    api.download_all_processed_files(
        server=server,
        task=task_id
    )
    print('-'*40)

