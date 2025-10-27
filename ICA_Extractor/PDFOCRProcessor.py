import json
import numpy as np
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import pdfplumber
from paddleocr import PaddleOCR
from PIL import Image
import io
import os
import utils


class PDFOCRProcessor:
    """
    Classe para processar PDFs escaneados usando PaddleOCR.
    Extrai texto e salva em formato .txt para uso posterior.
    """

    def __init__(self, input_dir: str, output_dir: str = None, use_gpu: bool = False):
        """
        Inicializa o processador de PDFs.

        Args:
            input_dir: Diretório com os PDFs originais
            output_dir: Diretório para salvar os .txt (padrão: input_dir/ocr_output)
            use_gpu: Se True, usa GPU (mais rápido). Se False, usa CPU
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "ocr_output"

        # Cria diretório de saída se não existir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Inicializa PaddleOCR
        print("🔧 Inicializando PaddleOCR...")
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # Detecta e corrige rotação de texto
            lang='pt',  # Português
            # use_gpu=use_gpu,  # GPU ou CPU
            # show_log=False,  # Não mostra logs verbosos
            det_db_thresh=0.3,  # Threshold de detecção (0.3 é bom para docs limpos)
            det_db_box_thresh=0.5  # Threshold de confiança da caixa
        )
        print("✅ PaddleOCR inicializado!")

        # Log de processamento
        self.log_file = self.output_dir / "processing_log.json"
        self.processing_log = self._load_log()

    def _load_log(self) -> Dict:
        """Carrega log de processamento anterior (para continuar de onde parou)."""
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"processed_files": [], "failed_files": [], "last_run": None}

    def _save_log(self):
        """Salva log de processamento."""
        self.processing_log["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.processing_log, f, indent=2, ensure_ascii=False)

    def get_pdf_files(self) -> List[Path]:
        """Retorna lista de todos os arquivos PDF no diretório de entrada."""
        pdf_files = list(self.input_dir.glob("*.pdf"))
        print(f"📁 {len(pdf_files)} arquivos PDF encontrados em {self.input_dir}")
        return pdf_files

    def extract_text_from_page(self, page_image: Image.Image) -> str:
        """
        Extrai texto de uma página usando PaddleOCR.

        Args:
            page_image: Imagem PIL da página

        Returns:
            Texto extraído da página
        """
        # Converte imagem PIL para bytes
        img_bytes = io.BytesIO()
        page_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)



        # Executa OCR
        # resultado = self.ocr.ocr(img_bytes.getvalue(), cls=True)
        # resultado = self.ocr.predict(img_bytes.getvalue())

        img_array = np.array(page_image)
        resultado = self.ocr.predict(img_array)
        # print(f'Tipo de resultado: {type(resultado)}')
        # print(f'Resultado OCR: {resultado[0]}')

        # Verifica se há resultado
        texto_linhas = []
        if resultado and len(resultado) > 0:
            print('Tem resultado')
            for pag in resultado:
                texto_linhas.append("\n".join(pag['rec_texts']))

        return "\n".join(texto_linhas)

    def process_single_pdf(self, pdf_path: Path, force_ocr: bool = False) -> bool:
        """
        Processa um único PDF.

        Args:
            pdf_path: Caminho do arquivo PDF
            force_ocr: Se True, força OCR mesmo se texto nativo existir

        Returns:
            True se processado com sucesso, False caso contrário
        """
        pdf_name = pdf_path.stem
        output_txt = self.output_dir / f"{pdf_name}.txt"

        # Verifica se já foi processado
        if pdf_name in self.processing_log["processed_files"] and output_txt.exists():
            print(f"⏭️  {pdf_name}.pdf já processado anteriormente. Pulando...")
            return True

        print(f"\n{'=' * 60}")
        print(f"📄 Processando: {pdf_name}.pdf")
        print(f"{'=' * 60}")

        try:
            textos_paginas = []

            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"📖 Total de páginas: {total_pages}")

                for i, pagina in enumerate(pdf.pages, start=1):
                    print(f"  🔍 Página {i}/{total_pages}...", end=" ")

                    # Tenta extrair texto nativo primeiro (mais rápido)
                    texto_nativo = pagina.extract_text()

                    if texto_nativo and texto_nativo.strip() and not force_ocr:
                        # Texto nativo encontrado e válido
                        textos_paginas.append(f"--- PÁGINA ---\n{texto_nativo}\n")
                        print("✅ (texto nativo)")
                    else:
                        # Precisa de OCR
                        print("🔎 (OCR necessário)...", end=" ")

                        # Converte página para imagem de alta resolução
                        img = pagina.to_image(resolution=300).original

                        # Extrai texto com OCR
                        texto_ocr = self.extract_text_from_page(img)

                        textos_paginas.append(f"--- PÁGINA ---\n{texto_ocr}\n")
                        print("✅")

            # Salva texto completo em arquivo .txt
            texto_completo = "\n".join(textos_paginas)

            with open(output_txt, 'w', encoding='utf-8') as f:
                f.write(texto_completo)

            # Atualiza log
            self.processing_log["processed_files"].append(pdf_name)
            self._save_log()

            print(f"✅ Texto salvo em: {output_txt.name}")
            print(f"📊 Total de caracteres extraídos: {len(texto_completo)}")

            return True

        except Exception as e:
            print(f"❌ ERRO ao processar {pdf_name}.pdf: {str(e)}")
            self.processing_log["failed_files"].append({
                "file": pdf_name,
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            self._save_log()
            return False

    def process_all_pdfs(self, force_ocr: bool = False, max_files: int = None):
        """
        Processa todos os PDFs do diretório de entrada.

        Args:
            force_ocr: Se True, força OCR mesmo se texto nativo existir
            max_files: Limite de arquivos a processar (útil para testes)
        """
        pdf_files = self.get_pdf_files()

        if max_files:
            pdf_files = pdf_files[:max_files]
            print(f"⚠️  Modo teste: processando apenas {max_files} arquivos")

        print(f"\n{'=' * 60}")
        print(f"🚀 INICIANDO PROCESSAMENTO EM LOTE")
        print(f"{'=' * 60}")
        print(f"📂 Diretório de entrada: {self.input_dir}")
        print(f"💾 Diretório de saída: {self.output_dir}")
        print(f"📊 Total de arquivos: {len(pdf_files)}")
        print(f"{'=' * 60}\n")

        inicio = datetime.now()
        sucessos = 0
        falhas = 0

        for idx, pdf_file in enumerate(pdf_files, start=1):
            print(f"\n[{idx}/{len(pdf_files)}]", end=" ")

            if self.process_single_pdf(pdf_file, force_ocr):
                sucessos += 1
            else:
                falhas += 1

        # Relatório final
        fim = datetime.now()
        duracao = fim - inicio

        print(f"\n\n{'=' * 60}")
        print(f"✨ PROCESSAMENTO CONCLUÍDO")
        print(f"{'=' * 60}")
        print(f"✅ Sucessos: {sucessos}")
        print(f"❌ Falhas: {falhas}")
        print(f"⏱️  Tempo total: {duracao}")
        print(f"📊 Média por arquivo: {duracao / len(pdf_files) if pdf_files else 0}")
        print(f"💾 Arquivos salvos em: {self.output_dir}")
        print(f"{'=' * 60}\n")

        # Mostra arquivos que falharam
        if self.processing_log["failed_files"]:
            print("\n⚠️  Arquivos com erro:")
            for failed in self.processing_log["failed_files"]:
                print(f"  - {failed['file']}: {failed['error']}")

    def get_text_from_processed_file(self, pdf_name: str) -> str:
        """
        Recupera o texto já processado de um PDF.

        Args:
            pdf_name: Nome do PDF (sem extensão)

        Returns:
            Texto extraído ou string vazia se não encontrado
        """
        txt_file = self.output_dir / f"{pdf_name}.txt"

        if txt_file.exists():
            with open(txt_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"⚠️  Arquivo {pdf_name}.txt não encontrado em {self.output_dir}")
            return ""


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Configuração
    utils.garantir_cwd_para("Repositorio-Semantico")
    INPUT_DIR = os.path.join(os.getcwd(), "ICA_Extractor", "ICAS")
    OUTPUT_DIR = os.path.join(os.getcwd(), "ICA_Extractor", "textos_extraidos")

    # Cria instância do processador
    processor = PDFOCRProcessor(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        use_gpu=False  # Mude para True se tiver GPU CUDA disponível
    )

    processor.process_all_pdfs()