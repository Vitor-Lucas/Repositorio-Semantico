import hashlib
import json
from datetime import datetime
from typing import List, Tuple, Dict
import utils
import os
import re


class ICAJSONGenerator:
    def __init__(self, input_dir: str, output_dir: str):
        """
        Classe que cria JSONs contendo os textos dos artigos a partir do
        texto extraido do arquivo, em .txt
        """
        print('Instância criada!')
        self.input_dir = os.path.join(os.getcwd(), input_dir)
        self.output_dir = os.path.join(os.getcwd(), output_dir)
        print(f'Caminho de entrada: {self.input_dir}')
        print(f'Caminho de saida: {self.output_dir}')

    def get_caminhos(self) -> list[str]:
        """Retorna uma lista com os caminhos completos de todos os arquivos dentro de um diretório."""
        extensoes = [".txt"]
        caminhos = []
        for raiz, _, arquivos in os.walk(self.input_dir):
            for arquivo in arquivos:
                if extensoes:
                    # verifica se o arquivo termina com uma das extensões permitidas
                    if not arquivo.lower().endswith(tuple(extensoes)):
                        continue
                caminhos.append(os.path.join(raiz, arquivo))
        return caminhos

    def process_documents(self):
        print('-'*40)
        print('INICIANDO PROCESSO DE CRIAÇÂO DE JSONS')
        print(f'Busca por caminhos iniciada no diretório: {self.input_dir}')
        print('Caminhos obtidos: ')
        print(self.get_caminhos())
        for i, file_path in enumerate(self.get_caminhos()):
            print('-'*20)
            print(f'Repetição {i}')
            print(f'Caminho de arquivo: {file_path}')

            # Textos separados por página
            with open(file_path, 'r', encoding='utf-8') as arquivo:
                textos = arquivo.read().split('--- PÁGINA ---')
            print(textos)
            primeira_pagina = textos[0]
            # revogada = get_ica_revogado(primeira_pagina)

            numero_ica = extrair_numero_ica(file_path)

            # Extrair data de publicação (você pode criar uma função específica para isso)
            data_publicacao = extrair_data_publicacao(primeira_pagina)

            artigos_estruturados = extrair_artigos_estruturados(textos, numero_ica, data_publicacao)

            salvar_artigos_json(
                artigos_estruturados,
                os.path.join(self.output_dir, fr"{numero_ica}.json"),
                'legivel'
            )

            print('-'*20)
        print('PROCESSO DE CRIAÇÂO DE JSONS ENCERRADO')
        print('-'*40)

def get_ica_revogado(texto: str):
    # print(texto)
    # print(texto.__contains__('Art'))
    # print(type(texto))
    print('-'*40)
    print('INICIANDO PROCESSO DE BUSCA POR REVOGAÇÃO')
    art_revogacao = None
    for num_art, texto_art in get_articles_simplificado(texto, True):
        print('-'*20)
        print(f'Artigo: {num_art}')
        print(f'Conteúdo: \n{texto_art[:min(len(texto_art), 400)]}')  # limita até 400 caracteres (poluição visual)

        if any(value.lower() in texto_art.lower() for value in ['Revoga', 'Revogado', 'Revogou']):
            print(f'Aqui é o artigo que revoga!!!! no artigo {num_art}')
            art_revogacao = (num_art, texto_art)
        print('-'*20)

    if not art_revogacao:
        print('ICA analisado não revoga nenhum outro ICA')
        print('-'*40)
        return None

    padrao = re.compile(
        r"""
        [Rr]evog(?:ar|a-se)\s+a\s+Portaria\s+          # início da frase
        (?P<orgao>[A-ZÇÕÉÊÂ]+\s*)?                    # órgão (ex: DECEA)
        n[°º]?\s*                                     # símbolo de número (n°, nº, n2 etc.)
        (?P<numero>[\d]+(?:\/[A-Z0-9]+)?)             # número e possível sufixo (801/ATAN3)
        ,?\s*de\s*(?P<data>[\d]{1,2}\s+de\s+\w+\s+de\s+\d{4})  # data
        (?:.*?(?:publicada\s+no.*?(?P<boletim>BCA|Boletim.*?)\s*(?:n[°º]?\s*[\d]+)?.*?)?)?
        [\.;]?                                         # final opcional
        """,
        re.VERBOSE
    )

    texto = texto.replace('\n','')
    resultados = []
    for match in padrao.finditer(texto):
        resultados.append({
            "orgao": match.group("orgao"),
            "numero": match.group("numero"),
            "data": match.group("data"),
            "boletim": match.group("boletim")
        })

    for result in resultados:
        print(result)
    return resultados


def get_articles_simplificado(texto: str, debug=False) -> list[str]:
    """
    Extrai todos os artigos (Art. X°, Artigo X, etc.) de um documento textual.
    Retorna lista de tuplas: (numero_artigo, texto_artigo).
    """
    # texto = limpar_texto_ocr(texto)

    # Expressão para capturar "Art." ou "Artigo", seguidos de número e símbolo opcional º/°
    padrao = r'(?m)^(Art(?:igo)?\.?\s*\d{1,3}\s*[º°]?)'

    matches = list(re.finditer(padrao, texto))

    if debug:
        print(f"🔍 {len(matches)} artigos encontrados")
        for m in matches:
            print(f"  -> '{m.group(1)}' (posição {m.start()})")

    artigos = []
    for i, match in enumerate(matches):
        inicio = match.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        numero = match.group(1).strip()
        conteudo = texto[inicio:fim].strip()
        artigos.append((numero, conteudo))

    return artigos


def extrair_numero_ica(caminho_completo: str) -> str:
    """
    Extrai o número do ICA do nome do arquivo.
    """
    nome_arquivo = os.path.basename(caminho_completo)
    print(nome_arquivo)
    nome_sem_ext = os.path.splitext(nome_arquivo)[0]
    print(nome_sem_ext)
    return nome_sem_ext


def extrair_data_publicacao(texto: str) -> str:
    """
    Extrai a data de publicação do documento.
    """
    # Padrão: "DD DE MMMM DE AAAA"
    padrao = re.compile(r'(\d{1,2})\s+[Dd][Ee]\s+(\w+)\s+[Dd][Ee]\s+(\d{4})')
    match = padrao.search(texto)

    if match:
        dia = match.group(1).zfill(2)
        mes_texto = match.group(2).lower()
        ano = match.group(3)

        meses = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }

        mes = meses.get(mes_texto, '01')
        return f"{dia}-{mes}-{ano}"

    return datetime.now().strftime("%d-%m-%Y")


def extrair_artigos_estruturados(textos: List[str], numero_ica: str, data_publicacao: str) -> List[Dict]:
    """
    Extrai todos os artigos de um documento ICA com seu contexto hierárquico completo.

    Args:
        textos: Lista de strings, cada uma representando o texto de uma página
        numero_ica: Número do ICA (ex: "ICA 96-1")
        data_publicacao: Data de publicação no formato "DD-MM-AAAA"

    Returns:
        Lista de dicionários com a estrutura padronizada dos artigos
    """

    # Juntar todas as páginas em um único texto
    texto_completo = "\n".join(textos)

    # PADRÃO MELHORADO: aceita I, l, 1, | (pipe) e variações
    padrao_titulo = re.compile(
        r'(?m)^T[ÍIi|l1]TULO\s*([IVXLCDM|]+|[0-9]+)\s*[-–—]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_capitulo = re.compile(
        r'(?m)^CAP[ÍIi|l1]TULO\s*([IVXLCDM|]+|[0-9]+)\s*[-–—]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_secao = re.compile(
        r'(?m)^SE[CcGg][ÇçCcGg]?[ÃãAaOo][Oo]?\s*([IVXLCDM|]+|[0-9]+)\s*[-–—]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_subsecao = re.compile(
        r'(?m)^SUBSE[CcGg][ÇçCcGg]?[ÃãAaOo][Oo]?\s*([IVXLCDM|]+|[0-9]+)\s*[-–—]?\s*(.*?)$',
        re.IGNORECASE
    )

    # Padrão para identificar artigos (mantém o seu)
    padrao_artigo = re.compile(
        r'(?m)^(Art\.?\s*\d{1,4}[ººº°]?\.?|Artigo\s+\d{1,4}[ººº°]?\.?)',
        re.IGNORECASE
    )

    # Debug: Verificar se está encontrando
    print(f'\n{"=" * 50}')
    print(f'ANÁLISE DO DOCUMENTO: {numero_ica}')
    print(f'{"=" * 50}')

    # Encontrar todas as ocorrências
    titulos = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_titulo.finditer(texto_completo)]
    print(f'\n📌 Títulos extraídos ({len(titulos)}):')
    for pos, num, nome in titulos[:5]:  # Mostra apenas os 5 primeiros
        print(f'   Posição {pos}: TÍTULO {num} - {nome[:50]}...')

    capitulos = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_capitulo.finditer(texto_completo)]
    print(f'\n📌 Capítulos extraídos ({len(capitulos)}):')
    for pos, num, nome in capitulos[:5]:
        print(f'   Posição {pos}: CAPÍTULO {num} - {nome[:50]}...')

    secoes = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_secao.finditer(texto_completo)]
    print(f'\n📌 Seções extraídas ({len(secoes)}):')
    for pos, num, nome in secoes[:5]:
        print(f'   Posição {pos}: SEÇÃO {num} - {nome[:50]}...')

    subsecoes = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_subsecao.finditer(texto_completo)]
    print(f'\n📌 Subseções extraídas ({len(subsecoes)}):')
    for pos, num, nome in subsecoes[:5]:
        print(f'   Posição {pos}: SUBSEÇÃO {num} - {nome[:50]}...')

    # Encontrar todos os artigos
    matches_artigos = list(padrao_artigo.finditer(texto_completo))
    print(f'\n📌 Artigos encontrados: {len(matches_artigos)}')

    artigos_estruturados = []
    data_acesso = datetime.now().strftime("%d-%m-%Y")

    for i, match in enumerate(matches_artigos):
        # Extrair número do artigo
        numero_artigo_raw = match.group(1).strip()
        # Normalizar o número do artigo
        numero_artigo = re.sub(r'[ºº°]', 'º', numero_artigo_raw)
        numero_artigo = re.sub(r'\s+', ' ', numero_artigo)
        if not numero_artigo.endswith('.'):
            numero_artigo = numero_artigo.rstrip('.')

        # Determinar início e fim do texto do artigo
        inicio_artigo = match.end()
        fim_artigo = matches_artigos[i + 1].start() if i + 1 < len(matches_artigos) else len(texto_completo)

        # Extrair texto do artigo
        texto_artigo = texto_completo[inicio_artigo:fim_artigo].strip()

        # Limpar excesso de espaços e quebras de linha
        texto_artigo = re.sub(r'\s+', ' ', texto_artigo)
        texto_artigo = texto_artigo.strip()

        # Concatenar número do artigo com o texto
        texto_completo_artigo = f"{numero_artigo} {texto_artigo}"

        # Determinar o contexto hierárquico
        posicao_artigo = match.start()

        # Encontrar o contexto atual
        titulo_atual = None
        capitulo_atual = None
        secao_atual = None
        subsecao_atual = None

        # Título
        for pos, num, nome in reversed(titulos):
            if pos < posicao_artigo:
                titulo_atual = f"TÍTULO {num}" + (f" - {nome}" if nome else "")
                break

        # Capítulo
        for pos, num, nome in reversed(capitulos):
            if pos < posicao_artigo:
                capitulo_atual = f"CAPÍTULO {num}" + (f" - {nome}" if nome else "")
                break

        # Seção
        for pos, num, nome in reversed(secoes):
            if pos < posicao_artigo:
                secao_atual = f"SEÇÃO {num}" + (f" - {nome}" if nome else "")
                break

        # Subseção
        for pos, num, nome in reversed(subsecoes):
            if pos < posicao_artigo:
                subsecao_atual = f"SUBSEÇÃO {num}" + (f" - {nome}" if nome else "")
                break

        # Gerar ID único
        # TODO Não ler os primeiros artigos, eles não servem pra salvar informações
        chave_id = f"{numero_ica}_{numero_artigo}"
        id_artigo = hashlib.md5(chave_id.encode('utf-8')).hexdigest()

        # Construir estrutura do artigo
        artigo_estruturado = {
            "id": id_artigo,
            "texto": texto_completo_artigo,
            "metadados": {
                "tipo_documento": "ICA",
                "nome": numero_ica,
                "artigo": numero_artigo,
                "data_publicacao": data_publicacao,
                "data_acesso": data_acesso,
                "contexto": {
                    "titulo": titulo_atual,
                    "capitulo": capitulo_atual,
                    "secao": secao_atual,
                    "subsecao": subsecao_atual
                }
            }
        }

        artigos_estruturados.append(artigo_estruturado)

    return artigos_estruturados


def salvar_artigos_json(artigos: List[Dict], caminho_saida: str, formato: str = 'compacto'):
    """
    Salva a lista de artigos em um arquivo JSON.

    Args:
        artigos: Lista de dicionários com os artigos estruturados
        caminho_saida: Caminho completo do arquivo de saída
        formato: 'compacto', 'legivel' ou 'estruturado'
    """
    # Garantir que o diretório de saída existe
    diretorio = os.path.dirname(caminho_saida)
    if diretorio and not os.path.exists(diretorio):
        os.makedirs(diretorio)
    if formato == 'compacto':
        # Formato compacto (sem indentação, economiza espaço)
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(artigos, f, ensure_ascii=False, separators=(',', ':'))

    elif formato == 'legivel':
        # Formato legível (com indentação)
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(artigos, f, ensure_ascii=False, indent=2)

    elif formato == 'estruturado':
        # Formato estruturado com metadados do documento
        documento_completo = {
            "metadados_documento": {
                "total_artigos": len(artigos),
                "data_extracao": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "nome_arquivo_origem": os.path.basename(caminho_saida).replace('_artigos.json', '.pdf')
            },
            "artigos": artigos
        }

        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(documento_completo, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(artigos)} artigos salvos em: {caminho_saida}")


if __name__ == '__main__':
    utils.garantir_cwd_para("Repositorio-Semantico")

    # TODO  criar um sistema de comparação entre a data de inicio de vigor do
    #  ICA pelo nome do arquivo e a data no texto mesmo

    ica_json_generator = ICAJSONGenerator(
        input_dir=r'ICA_Extractor\textos_extraidos',
        output_dir=r"JSONs\ICA"
    )
    ica_json_generator.process_documents()



