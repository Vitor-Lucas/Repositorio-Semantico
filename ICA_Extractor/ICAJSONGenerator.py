import hashlib
import json
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import utils
from utils import print_mid_warning, print_serious_warning, print_info, print_green, print_delimiter, print_cyan
import os
import sys
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
                    if not arquivo.lower().endswith(tuple(extensoes)):
                        continue
                caminhos.append(os.path.join(raiz, arquivo))
        return caminhos

    def process_documents(self, modo='hibrido'):
        """
        Processa documentos e gera JSONs.

        Args:
            modo: 'artigos' | 'secoes' | 'hibrido' | 'auto'
            - artigos: usa extrair_artigos_estruturados()
            - secoes: usa extrair_secoes_estruturadas()
            - hibrido: usa ambas funções (artigos + seções)
            - auto: detecta automaticamente (TODO: implementar)
        """
        print('-' * 40)
        print(f'INICIANDO PROCESSO DE CRIAÇÃO DE JSONS - MODO: {modo.upper()}')
        print(f'Busca por caminhos iniciada no diretório: {self.input_dir}')
        print('Caminhos obtidos: ')
        print(self.get_caminhos())

        for i, file_path in enumerate(self.get_caminhos()):
            print('-' * 20)
            print(f'Repetição {i}')
            print(f'Caminho de arquivo: {file_path}')

            with open(file_path, 'r', encoding='utf-8') as arquivo:
                texto_cru = arquivo.read()
                textos = texto_cru.split('--- PÁGINA ---')

            numero_ica, data_vigencia_inicio, data_vigencia_fim, categoria = separar_caminho_arquivo(file_path)

            if data_vigencia_inicio:
                data_vigencia_inicio = data_vigencia_inicio[:2] + '-' + data_vigencia_inicio[
                                                                        2:4] + '-' + data_vigencia_inicio[4:]
            if data_vigencia_fim:
                data_vigencia_fim = data_vigencia_fim[:2] + '-' + data_vigencia_fim[2:4] + '-' + data_vigencia_fim[4:]

            primeira_pagina = textos[0]
            data_publicacao = extrair_data_publicacao(primeira_pagina)

            if not data_vigencia_inicio:
                data_vigencia_inicio = extrair_data_vigencia(
                    textos=textos[:min(4, len(textos))],
                    data_publicacao=data_publicacao
                )
                print(f'Data de publicação: {data_publicacao}')
                print(f"Data vigencia determinada!: {data_vigencia_inicio}")

            citacoes_estruturadas = []

            if modo == 'artigos':
                citacoes_estruturadas = extrair_artigos_estruturados(
                    textos=textos,
                    numero_ica=numero_ica,
                    data_publicacao=data_publicacao,
                    data_vigor_inicio=data_vigencia_inicio,
                    data_vigor_fim=data_vigencia_fim,
                    categoria=categoria
                )

            elif modo == 'secoes':
                citacoes_estruturadas = extrair_secoes_estruturadas(
                    texto_cru=texto_cru,
                    numero_ica=numero_ica,
                    data_publicacao=data_publicacao,
                    data_vigor_inicio=data_vigencia_inicio,
                    data_vigor_fim=data_vigencia_fim,
                    categoria=categoria
                )

            elif modo == 'hibrido':

                artigos = extrair_artigos_estruturados(
                    textos=textos,
                    numero_ica=numero_ica,
                    data_publicacao=data_publicacao,
                    data_vigor_inicio=data_vigencia_inicio,
                    data_vigor_fim=data_vigencia_fim,
                    categoria=categoria
                )

                # secoes = extrair_secoes_estruturadas(
                #     texto_cru=texto_cru,
                #     numero_ica=numero_ica,
                #     data_publicacao=data_publicacao,
                #     data_vigor_inicio=data_vigencia_inicio,
                #     data_vigor_fim=data_vigencia_fim,
                #     categoria=categoria
                # )

                secoes = extrair_secoes_flat_para_rag(
                    texto_cru=texto_cru,
                    numero_ica=numero_ica,
                    data_publicacao=data_publicacao,
                    data_vigor_inicio=data_vigencia_inicio,
                    data_vigor_fim=data_vigencia_fim,
                    categoria=categoria
                )

                citacoes_estruturadas = artigos + secoes

            elif modo == 'auto':
                print("⚠️ Modo AUTO ainda não implementado. Usando modo HÍBRIDO.")
                citacoes_estruturadas = self._processar_modo_hibrido(
                    textos, numero_ica, data_publicacao,
                    data_vigencia_inicio, data_vigencia_fim, categoria
                )

            salvar_artigos_json(
                citacoes_estruturadas,
                os.path.join(self.output_dir, f"{numero_ica}.json"),
                'legivel'
            )

            print('-' * 20)
        print('PROCESSO DE CRIAÇÃO DE JSONS ENCERRADO')
        print('-' * 40)


def separar_caminho_arquivo(file_path: str, sep: str = '_') -> list:
    file_name = os.path.basename(file_path)
    print(file_name)
    caminho_sem_extensao = file_name.split('.')[0]
    return caminho_sem_extensao.split(sep)


def extrair_data_publicacao(texto: str) -> str:
    """Extrai a data de publicação do documento."""
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


def calcular_nivel_hierarquico(numero_secao: str) -> int:
    """
    Retorna o nível hierárquico de uma seção.
    Exemplos: "1" -> 1, "1.1" -> 2, "1.1.1" -> 3
    """
    return len(numero_secao.split('.'))


def extrair_todas_secoes_numeradas(texto: str) -> List[Tuple[int, str, str]]:
    """
    Extrai todas as seções numeradas do texto.
    Returns: Lista de tuplas (posicao, numero_secao, titulo_secao)
    """
    padrao = re.compile(
        r'^(\d+(?:\.\d+)*)\s+([A-ZÀÂÃÇÉÊÍÓÔÕÚ][^\n]+?)(?=\n|$)',
        re.MULTILINE
    )

    # padrao = re.compile(
    #     r'^(\d+(?:\.\d+)*)\s+([A-ZÀÂÃÇÉÊÍÓÔÕÚÇ0-9\s\-,–/()]+)$',  # funciona bem
    #     re.MULTILINE
    # )

    # padrao = re.compile(
    #     r'^\s*(\d+(?:\.\d+)*)\s+([A-ZÀ-ÝÇ0-9\s\-,–/()]+?)\s*$', # funciona melhor, pega os que tem acentos
    #     re.MULTILINE
    # )

    secoes = []
    for match in padrao.finditer(texto):
        posicao = match.start()
        numero = match.group(1).strip()
        titulo = match.group(2).strip()
        # subseções sem titulo estão com o texto do lado do numero minuscula
        if not titulo.isupper():
            titulo = ""
        secoes.append((posicao, numero, titulo))
        # (7469, '1.5.5', 'PRAZO DE VALIDADE DE CALIBRAÇÃO')
    # print("\n".join([str(val) for val in secoes]))
    return secoes


def tem_subsecoes_numeradas(numero_secao: str, todas_secoes: List[Tuple]) -> bool:
    """Verifica se uma seção possui subseções numeradas."""
    nivel_atual = calcular_nivel_hierarquico(numero_secao)

    for _, num, _ in todas_secoes:
        if num.startswith(numero_secao + '.'):
            nivel_candidato = calcular_nivel_hierarquico(num)
            if nivel_candidato == nivel_atual + 1:
                return True

    return False


def extrair_texto_secao(
        numero_secao: str,
        posicao_inicio: int,
        texto_completo: str,
        todas_secoes: List[Tuple]
) -> str:
    """
    ✅ FUNÇÃO CORRIGIDA - FINAL
    Extrai o texto de uma seção removendo APENAS a linha do cabeçalho.
    """
    nivel_atual = calcular_nivel_hierarquico(numero_secao)

    # Encontrar posição final
    posicao_fim = len(texto_completo)

    print("-"*40)
    # for pos, num, _ in todas_secoes:
    #     if pos > posicao_inicio:
    #         # print(f'pos: {pos}, num: {num}, texto: {_[:30]}')
    #         nivel_candidato = calcular_nivel_hierarquico(num)
    #         if nivel_candidato <= nivel_atual:
    #             posicao_fim = pos
    #             print(f'Encontrado o fim da seção: {pos}, {num}, {_}')
    #             break

    # Pega o trecho entre a seção atual e a mais próxima
    menor_pos = posicao_fim
    for pos, num, _ in todas_secoes:
        if posicao_inicio < pos < menor_pos:
            menor_pos = pos
    posicao_fim = menor_pos

    # Extrair texto completo da seção
    texto_bruto = texto_completo[posicao_inicio:posicao_fim].strip()
    # print("-"*30)
    # print(texto_bruto)
    # print('-'*30)
    # Remove primeira linha (cabeçalho)
    linhas = texto_bruto.split('\n')

    # se existe linha e ela começa com algum numero ("2.1 FINALIDADE")
    if linhas and re.match(r'^\d+(?:\.\d+)*\s+.+', linhas[0]):
        # print('Sessão nova!')
        # print('\n'.join(linhas[1:]).strip())
        return '\n'.join(linhas[1:]).strip()
    else:
        # print('Não é sessão')
        # print(texto_bruto)
        return texto_bruto


def extrair_secoes_flat_para_rag(
        texto_cru: str,
        numero_ica: str,
        data_publicacao: str,
        data_vigor_inicio: str,
        data_vigor_fim: str,
        categoria: str
) -> List[Dict]:
    """
    ✅ FUNÇÃO PRINCIPAL - Arquitetura FLAT para RAG
    Extrai todas as seções/subseções em estrutura achatada otimizada.
    """
    print(f'\n{"=" * 50}')
    print(f'EXTRAÇÃO DE SEÇÕES FLAT (RAG): {numero_ica}')
    print(f'{"=" * 50}')

    textos = texto_cru.split('--- PÁGINA ---')

    # Remover SUMÁRIO (página 6 em geral)

    if len(textos) > 6:
        textos.pop(0)  # primeira pagina
        textos.pop(0)  # pagina em branco
        textos.pop(0)  # primeira pagina denovo
        textos.pop(0)  # pagina em branco
        textos.pop(3)  # remover o sumário
        # del textos[7]
        print('Sumário removido!!')

    texto_completo = "\n".join(textos)

    # TODO pensar em talvez deletar as paginas que tem referências
    # TODO talvez deletar os anexos ou arrumar um jeito de fazer um JSON deles?

    todas_secoes = extrair_todas_secoes_numeradas(texto_completo)
    print(f'\n📋 Total de seções numeradas encontradas: {len(todas_secoes)}')
    print('\n🔍 Primeiras 10 seções detectadas:')
    for pos, num, titulo in todas_secoes[:10]:
        nivel = calcular_nivel_hierarquico(num)
        print(f'   {"  " * (nivel - 1)}├─ {num} - {titulo[:60]}...')

    secoes_flat = []
    data_acesso = datetime.now().strftime("%d-%m-%Y")

    for posicao, numero_secao, titulo_secao in todas_secoes:
        nivel = calcular_nivel_hierarquico(numero_secao)

        # Extrair texto próprio (sem subseções)
        texto_proprio = extrair_texto_secao(
            numero_secao, posicao, texto_completo, todas_secoes
        )

        # Extrair texto com subseções (apenas para nível 1 ou seções com filhos)
        tem_filhos = tem_subsecoes_numeradas(numero_secao, todas_secoes)
        texto_com_filhos = None

        if nivel == 1 or tem_filhos:
            texto_com_filhos = extrair_texto_com_subsecoes(
                numero_secao, posicao, texto_completo, todas_secoes
            )

        # Encontrar subseções diretas
        subsecoes_diretas = encontrar_subsecoes_diretas(
            numero_secao, todas_secoes
        )

        # Construir caminho numérico
        partes = numero_secao.split('.')
        caminho_numerico = ' > '.join([
            '.'.join(partes[:i + 1]) for i in range(len(partes))
        ])

        # Construir caminho de títulos
        caminho_titulos = construir_caminho_titulos(
            numero_secao, todas_secoes
        )

        # Determinar seção raiz e pai
        secao_raiz = partes[0]
        secao_pai = '.'.join(partes[:-1]) if len(partes) > 1 else None

        # Criar ID único
        chave_id = f"{numero_ica}_secao_{numero_secao}"
        id_secao = hashlib.md5(chave_id.encode('utf-8')).hexdigest()

        # Tipo de conteúdo
        tipo_conteudo = "secao" if nivel == 1 else "subsecao"

        secao_flat = {
            "id": id_secao,
            "tipo_conteudo": tipo_conteudo,
            "identificacao": numero_secao,
            "titulo": titulo_secao if titulo_secao else None,
            "nivel_hierarquico": nivel,
            "texto_completo": texto_proprio,
            "texto_com_subsecoes": texto_com_filhos,
            "texto_para_embedding": "",  # Será preenchido depois
            "estrategia_embedding": "",  # Será preenchido depois
            "hierarquia": {
                "caminho_numerico": caminho_numerico,
                "caminho_titulos": caminho_titulos,
                "secao_raiz": secao_raiz,
                "secao_pai": secao_pai,
                "subsecoes_diretas": subsecoes_diretas
            },
            "metadados": {
                "tipo_documento": "ICA",
                "nome_documento": numero_ica,
                "categoria": categoria,
                "data_publicacao": data_publicacao,
                "data_vigencia_inicio": data_vigor_inicio,
                "data_vigencia_fim": data_vigor_fim,
                "data_acesso": data_acesso,
                "revogado": bool(data_vigor_fim),
                "num_tokens_texto_completo": 0,  # Será calculado depois
                "num_tokens_com_subsecoes": 0,  # Será calculado depois
                "num_tokens_para_embedding": 0  # Será calculado depois
            }
        }

        secoes_flat.append(secao_flat)

    print(f'\n✅ Total de seções flat estruturadas: {len(secoes_flat)}')
    return secoes_flat


def extrair_texto_com_subsecoes(
        numero_secao: str,
        posicao_inicio: int,
        texto_completo: str,
        todas_secoes: List[Tuple]
) -> str:
    """
    Extrai o texto completo de uma seção INCLUINDO todas as subseções.
    """
    nivel_atual = calcular_nivel_hierarquico(numero_secao)

    # Encontrar posição final (próxima seção de mesmo nível ou superior)
    posicao_fim = len(texto_completo)

    for pos, num, _ in todas_secoes:
        if pos > posicao_inicio:
            nivel_candidato = calcular_nivel_hierarquico(num)
            if nivel_candidato <= nivel_atual:
                posicao_fim = pos
                break

    # Extrair texto completo
    texto_bruto = texto_completo[posicao_inicio:posicao_fim].strip()

    # Remover apenas primeira linha (cabeçalho)
    linhas = texto_bruto.split('\n')

    if linhas and re.match(r'^\d+(?:\.\d+)*\s+.+', linhas[0]):
        return '\n'.join(linhas[1:]).strip()
    else:
        return texto_bruto


def construir_caminho_titulos(
        numero_secao: str,
        todas_secoes: List[Tuple]
) -> str:
    """Constrói o caminho completo de títulos."""
    partes = numero_secao.split('.')
    titulos = []

    for i in range(len(partes)):
        num_busca = '.'.join(partes[:i + 1])
        for _, num, titulo in todas_secoes:
            if num == num_busca:
                titulos.append(titulo)
                break

    return ' > '.join(titulos)


def extrair_texto_introducao(
        texto_secao: str,
        primeira_subsecao_pos: Optional[int]
) -> Optional[str]:
    """Extrai o texto introdutório de uma seção (antes da primeira subseção)."""
    if primeira_subsecao_pos is None:
        return None

    linhas = texto_secao.split('\n')
    if len(linhas) < 2:
        return None

    texto_intro = []
    for linha in linhas:
        # Parar se encontrou subseção numerada
        if re.match(r'^\d+\.\d+', linha):
            break
        if linha.strip():
            texto_intro.append(linha)

    resultado = '\n'.join(texto_intro).strip()
    return resultado if resultado else None


def encontrar_subsecoes_diretas(
        numero_secao: str,
        todas_secoes: List[Tuple]
) -> List[str]:
    """Retorna lista de identificadores das subseções diretas."""
    nivel_atual = calcular_nivel_hierarquico(numero_secao)
    subsecoes = []

    for _, num, _ in todas_secoes:
        if num.startswith(numero_secao + '.'):
            nivel_candidato = calcular_nivel_hierarquico(num)
            if nivel_candidato == nivel_atual + 1:
                subsecoes.append(num)

    return subsecoes


def extrair_subsecoes(
        numero_secao: str,
        texto_completo: str,
        todas_secoes: List[Tuple],
        posicao_secao: int
) -> List[Dict]:
    """
    ✅ FUNÇÃO CORRIGIDA - Agora recebe texto_completo!
    Extrai lista de subseções de uma seção pai.
    """
    nivel_pai = calcular_nivel_hierarquico(numero_secao)
    subsecoes = []

    for pos, num, titulo in todas_secoes:
        if num.startswith(numero_secao + '.'):
            nivel_candidato = calcular_nivel_hierarquico(num)
            if nivel_candidato == nivel_pai + 1:
                # ✅ CORREÇÃO: Agora passa texto_completo em vez de texto_secao
                texto_subsecao = extrair_texto_secao(num, pos, texto_completo, todas_secoes)

                subsecoes.append({
                    "identificacao": num,
                    "titulo": titulo if titulo else None,
                    "texto": texto_subsecao,
                    "nivel": nivel_candidato
                })

    return subsecoes


def montar_contexto_hierarquico(
        numero_secao: str,
        posicao: int,
        todas_secoes: List[Tuple],
        texto_completo: str
) -> Dict:
    """Monta o contexto hierárquico completo de uma seção."""
    nivel_atual = calcular_nivel_hierarquico(numero_secao)
    partes = numero_secao.split('.')

    contexto = {
        "capitulo": None,
        "secao_pai": None,
        "hierarquia_completa": None
    }

    # Encontrar capítulo (nível 1)
    if nivel_atual >= 1:
        capitulo_num = partes[0]
        for pos, num, titulo in todas_secoes:
            if num == capitulo_num and pos < posicao:
                contexto["capitulo"] = f"{num} - {titulo}" if titulo else num
                break

    # Encontrar seção pai
    if nivel_atual >= 2:
        secao_pai_num = '.'.join(partes[:-1])
        for pos, num, titulo in todas_secoes:
            if num == secao_pai_num and pos < posicao:
                contexto["secao_pai"] = f"{num} - {titulo}" if titulo else num
                break

    # Montar hierarquia completa
    hierarquia = []
    for i in range(1, nivel_atual + 1):
        parte_num = '.'.join(partes[:i])
        hierarquia.append(parte_num)
    contexto["hierarquia_completa"] = ' > '.join(hierarquia)

    return contexto


def extrair_artigos_estruturados(textos: List[str], numero_ica: str, data_publicacao: str,
                                 data_vigor_inicio: str, data_vigor_fim: str, categoria: str) -> List[Dict]:
    """Extrai todos os artigos de um documento ICA com contexto hierárquico."""
    texto_completo = "\n".join(textos)

    padrao_titulo = re.compile(
        r'(?m)^T[ÍIi|l1]TULO\s*([IVXLCDM|]+|[0-9]+)\s*[-—–]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_capitulo = re.compile(
        r'(?m)^CAP[ÍIi|l1]TULO\s*([IVXLCDM|]+|[0-9]+)\s*[-—–]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_secao = re.compile(
        r'(?m)^S[Ee][ÇcCc]?[ÃãAaOo][Oo]?\s*([IVXLCDM]+|[0-9]+)\s*[-—–]?\s*(.*?)$',
        re.IGNORECASE
    )

    padrao_subsecao = re.compile(
        r'(?ms)^SUBS[Ee][ÇCc]?[ÃãAaOo][Oo]?\s*(?:[-—–]?\s*)?([IVXLCDM]+|[0-9]+)\s*[-—–]?\s*(.*?)(?=\n\S|$)',
        re.IGNORECASE
    )

    padrao_artigo = re.compile(
        r'(?m)^(Art\.?\s*\d{1,4}[ºººº°]?\.?|Artigo\s+\d{1,4}[ºººº°]?\.?)',
        re.IGNORECASE
    )

    titulos = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_titulo.finditer(texto_completo)]
    capitulos = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_capitulo.finditer(texto_completo)]
    secoes = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_secao.finditer(texto_completo)]
    subsecoes = [(m.start(), m.group(1), m.group(2).strip()) for m in padrao_subsecao.finditer(texto_completo)]
    matches_artigos = list(padrao_artigo.finditer(texto_completo))

    artigos_estruturados = []
    data_acesso = datetime.now().strftime("%d-%m-%Y")

    for i, match in enumerate(matches_artigos):
        numero_artigo_raw = match.group(1).strip()
        numero_artigo = re.sub(r'[ºººº°]', 'º', numero_artigo_raw)
        numero_artigo = re.sub(r'\s+', ' ', numero_artigo)
        if not numero_artigo.endswith('.'):
            numero_artigo = numero_artigo.rstrip('.')

        inicio_artigo = match.end()
        fim_artigo = matches_artigos[i + 1].start() if i + 1 < len(matches_artigos) else len(texto_completo)

        texto_artigo = texto_completo[inicio_artigo:fim_artigo].strip()
        texto_artigo = re.sub(r'\s+', ' ', texto_artigo)
        texto_completo_artigo = f"{numero_artigo} {texto_artigo}"

        posicao_artigo = match.start()

        titulo_atual = None
        capitulo_atual = None
        secao_atual = None
        subsecao_atual = None

        for pos, num, nome in reversed(titulos):
            if pos < posicao_artigo:
                titulo_atual = f"TÍTULO {num}" + (f" - {nome}" if nome else "")
                break

        for pos, num, nome in reversed(capitulos):
            if pos < posicao_artigo:
                capitulo_atual = f"CAPÍTULO {num}" + (f" - {nome}" if nome else "")
                break

        for pos, num, nome in reversed(secoes):
            if pos < posicao_artigo:
                secao_atual = f"SEÇÃO {num}" + (f" - {nome}" if nome else "")
                break

        for pos, num, nome in reversed(subsecoes):
            if pos < posicao_artigo:
                subsecao_atual = f"SUBSEÇÃO {num}" + (f" - {nome}" if nome else "")
                break

        chave_id = f"{numero_ica}_{numero_artigo}"
        id_artigo = hashlib.md5(chave_id.encode('utf-8')).hexdigest()

        artigo_estruturado = {
            "id": id_artigo,
            "texto": texto_completo_artigo,
            "metadados": {
                "tipo_documento": "ICA",
                "nome": numero_ica,
                "identificação": numero_artigo,
                "data_publicacao": data_publicacao,
                "data_vigencia_inicio": data_vigor_inicio,
                "data_vigencia_fim": data_vigor_fim,
                "data_acesso": data_acesso,
                "categoria": categoria,
                "contexto": {
                    "titulo": titulo_atual,
                    "capitulo": capitulo_atual,
                    "secao": secao_atual,
                    "subsecao": subsecao_atual
                },
                "revogado": True if data_vigor_fim else False
            }
        }

        artigos_estruturados.append(artigo_estruturado)

    return artigos_estruturados


def extrair_secoes_estruturadas(
        texto_cru: str,
        numero_ica: str,
        data_publicacao: str,
        data_vigor_inicio: str,
        data_vigor_fim: str,
        categoria: str
) -> List[Dict]:
    """
    ✅ FUNÇÃO PRINCIPAL CORRIGIDA
    Extrai todas as seções/subseções com estrutura completa.
    """
    print(f'\n{"=" * 50}')
    print(f'EXTRAÇÃO DE SEÇÕES NUMERADAS: {numero_ica}')
    print(f'{"=" * 50}')
    textos = texto_cru.split('--- PÁGINA ---')

    # ✅ FILTRO: Remover seção SUMÁRIO
    textos.pop(6)

    texto_completo = "\n".join(textos)
    # print(texto_completo)
    # sys.exit()
    todas_secoes = extrair_todas_secoes_numeradas(texto_completo)

    print(f'\n📋 Total de seções numeradas encontradas: {len(todas_secoes)}')
    print('\n🔍 Primeiras 10 seções detectadas:')
    for pos, num, titulo in todas_secoes[:10]:
        nivel = calcular_nivel_hierarquico(num)
        print(f'   {"  " * (nivel - 1)}├─ {num} - {titulo[:60]}...')

    secoes_estruturadas = []
    data_acesso = datetime.now().strftime("%d-%m-%Y")

    for posicao, numero_secao, titulo_secao in todas_secoes:
        nivel = calcular_nivel_hierarquico(numero_secao)

        # ✅ Usar função corrigida
        texto_secao = extrair_texto_secao(
            numero_secao, posicao, texto_completo, todas_secoes
        )

        tem_filhos = tem_subsecoes_numeradas(numero_secao, todas_secoes)

        lista_subsecoes = []
        if tem_filhos:
            lista_subsecoes = extrair_subsecoes(
                numero_secao, texto_completo, todas_secoes, posicao
            )

        texto_intro = None
        if tem_filhos and lista_subsecoes:
            # ✅ CORREÇÃO: Passa o número da subseção (string) em vez de posição
            numero_primeira_subsecao = lista_subsecoes[0]["identificacao"]
            texto_intro = extrair_texto_introducao(texto_secao, numero_primeira_subsecao)

        contexto = montar_contexto_hierarquico(
            numero_secao, posicao, todas_secoes, texto_completo
        )

        chave_id = f"{numero_ica}_{numero_secao}"
        id_secao = hashlib.md5(chave_id.encode('utf-8')).hexdigest()

        secao_estruturada = {
            "id": id_secao,
            "identificacao": numero_secao,
            "titulo": titulo_secao if titulo_secao else None,
            "nivel": nivel,
            "texto_introducao": texto_intro,
            "texto_completo": texto_secao,
            "subsecoes": lista_subsecoes,
            "metadados": {
                "tipo_documento": "ICA",
                "nome": numero_ica,
                "data_publicacao": data_publicacao,
                "data_vigencia_inicio": data_vigor_inicio,
                "data_vigencia_fim": data_vigor_fim,
                "data_acesso": data_acesso,
                "categoria": categoria,
                "contexto": contexto,
                "revogado": True if data_vigor_fim else False
            }
        }

        secoes_estruturadas.append(secao_estruturada)

    print(f'\n✅ Total de seções estruturadas: {len(secoes_estruturadas)}')
    return secoes_estruturadas


def extrair_data_vigencia(textos: list[str], data_publicacao: str) -> Optional[str]:
    """Extrai a data de vigência de documentos ICA/Portarias."""
    texto_completo = "\n".join(textos)
    texto_limpo = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', texto_completo)

    padrao_artigo_vigencia = re.compile(
        r'Art\.?\s*\d{1,3}[ºººº°]?\s*(.{0,200}?entra\s+em\s+vigor.{0,200}?)(?=Art\.|$)',
        re.IGNORECASE | re.DOTALL
    )

    match_artigo = padrao_artigo_vigencia.search(texto_limpo)
    if not match_artigo:
        return None

    texto_vigencia = match_artigo.group(1)

    padrao_data_publicacao = re.compile(
        r'entra\s+em\s+vigor\s+(?:na\s+data|no\s+ato)\s+de\s+sua\s+publicação',
        re.IGNORECASE
    )

    if padrao_data_publicacao.search(texto_vigencia):
        return data_publicacao

    padrao_data_especifica = re.compile(
        r'entra\s+em\s+vigor\s+em\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
        re.IGNORECASE
    )

    match_data = padrao_data_especifica.search(texto_vigencia)
    if match_data:
        dia = match_data.group(1).zfill(2)
        mes_texto = match_data.group(2).lower()
        ano = match_data.group(3)

        meses = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
            'abril': '04', 'maio': '05', 'junho': '06',
            'julho': '07', 'agosto': '08', 'setembro': '09',
            'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }

        mes = meses.get(mes_texto, '01')
        return f"{dia}-{mes}-{ano}"

    return None


def salvar_artigos_json(artigos: List[Dict], caminho_saida: str, formato: str = 'compacto'):
    """Salva a lista de artigos em arquivo JSON."""
    diretorio = os.path.dirname(caminho_saida)
    if diretorio and not os.path.exists(diretorio):
        os.makedirs(diretorio)

    if formato == 'compacto':
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(artigos, f, ensure_ascii=False, separators=(',', ':'))
    elif formato == 'legivel':
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(artigos, f, ensure_ascii=False, indent=2)
    elif formato == 'estruturado':
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

    ica_json_generator = ICAJSONGenerator(
        input_dir=r'ICA_Extractor\textos_diferenciados',
        output_dir=r"JSONs\ICA"
    )
    ica_json_generator.process_documents()
