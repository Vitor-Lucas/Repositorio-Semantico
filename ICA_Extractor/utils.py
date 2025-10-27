import os


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