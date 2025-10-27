# Sistema RAG para Consulta Temporal de Normas de Aviação Brasileira

Sistema de Retrieval-Augmented Generation (RAG) especializado para consulta de normas regulatórias da aviação civil brasileira, com suporte a versionamento temporal.

## Características Principais

- ✅ **Busca Semântica** com Legal-BERTimbau (especializado em textos jurídicos PT-BR)
- ✅ **Versionamento Temporal** - consulta normas vigentes em datas específicas
- ✅ **Vector Database** Qdrant com índices otimizados (HNSW)
- ✅ **LLM Open-Source** Llama 3.1 via Ollama
- ✅ **API REST** com autenticação e rate limiting
- ✅ **Parsers Automáticos** para LexML (XML) e PDFs (ICAs)
- ✅ **Escalável** para centenas de milhares de vetores

## Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| Vector Database | Qdrant (Docker) |
| Embeddings | Legal-BERTimbau-sts-large-ma-v3 (1024-dim) |
| LLM | Llama 3.1 (8B/70B) via Ollama |
| API | FastAPI + Uvicorn/Gunicorn |
| Parsing | lxml, PyPDF2, pdfplumber |
| Language | Python 3.10+ |

## Requisitos

### Hardware
- **CPU:** 8+ cores
- **RAM:** 16 GB mínimo, 64 GB recomendado
- **GPU:** NVIDIA com 10+ GB VRAM (Llama 8B) ou 80+ GB VRAM (Llama 70B distribuído)
- **Storage:** 100 GB SSD

### Software
- Python 3.10+
- Docker e Docker Compose
- CUDA 11.8+ (para GPU)
- Ollama

## Instalação Rápida

### 1. Clone o Repositório

```bash
git clone https://github.com/your-org/aviation-rag-system.git
cd aviation-rag-system
```

### 2. Ambiente Python

```bash
# Criar virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Subir Qdrant (Docker)

```bash
docker-compose up -d qdrant

# Verificar
curl http://localhost:6333/
```

### 4. Instalar Ollama e Llama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Baixar Llama 3.1 8B
ollama pull llama3.1:8b

# Testar
ollama run llama3.1:8b "Olá"
```

### 5. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env  # Editar API_KEY e outras configs
```

### 6. Inicializar Sistema

```bash
# Criar collection no Qdrant
python scripts/setup_qdrant.py

# Ingerir dados (exemplo)
python scripts/ingest_lexml.py --keywords "aviação,aeronave,ANAC" --limit 100

# Testar sistema
python scripts/test_system.py
```

### 7. Rodar API

```bash
# Desenvolvimento
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# Produção
gunicorn api.server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Uso da API

### Endpoint Principal: Busca de Regulações

```python
import requests

headers = {"X-API-Key": "sua-api-key"}

response = requests.post(
    "http://localhost:8000/api/search-regulations",
    headers=headers,
    json={
        "query": "requisitos de tripulação para A320",
        "date": "2023-05-15",  # Normas vigentes nesta data
        "limit": 5,
        "filters": {
            "category": "crew_requirements",
            "aircraft_type": "A320"
        }
    }
)

data = response.json()
print("Resposta:", data["answer"])
print("Fontes:", [s["regulation_id"] for s in data["sources"]])
```

### Resposta Exemplo

```json
{
    "answer": "Segundo o RBAC 121, Art. 359, versão vigente em 15/05/2023, aeronaves A320 devem ter no mínimo 1 comissário para cada 50 assentos de passageiros...",
    "sources": [
        {
            "regulation_id": "rbac-121-art-359",
            "version": "2022-08-15",
            "text": "Art. 359. Cada detentor de certificado...",
            "similarity_score": 0.89,
            "metadata": {
                "effective_date": "2022-08-15T00:00:00Z",
                "expiry_date": null,
                "category": "crew_requirements"
            }
        }
    ],
    "processing_time_ms": 3245
}
```

## Estrutura do Projeto

```
aviation-rag-system/
├── documentation.tex           # Documentação técnica completa (LaTeX)
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── config.py
│
├── models/                     # Modelos de ML
│   ├── embeddings.py          # Legal-BERTimbau
│   └── llm.py                 # Llama via Ollama
│
├── parsers/                    # Parsers de documentos
│   ├── lexml_scraper.py       # Scraper API LexML
│   ├── lexml_parser.py        # Parser XML → Artigos
│   ├── pdf_parser.py          # Parser PDFs (ICAs)
│   └── temporal_extractor.py  # Extração de datas
│
├── database/                   # Gerenciamento Qdrant
│   ├── qdrant_manager.py      # CRUD operations
│   └── versioning.py          # Versionamento temporal
│
├── pipeline/                   # Pipeline de processamento
│   ├── chunking.py            # Chunking por artigos
│   └── ingestion.py           # Pipeline end-to-end
│
├── search/                     # Busca e RAG
│   ├── vector_search.py       # Busca vetorial temporal
│   └── rag.py                 # RAG pipeline
│
├── api/                        # API REST
│   ├── auth.py                # Autenticação API Key
│   ├── schemas.py             # Pydantic models
│   └── server.py              # FastAPI app
│
├── scripts/                    # Scripts utilitários
│   ├── setup_qdrant.py        # Setup inicial
│   ├── ingest_lexml.py        # Ingestão LexML
│   ├── ingest_pdfs.py         # Ingestão PDFs
│   └── test_system.py         # Testes
│
└── tests/                      # Testes unitários
    ├── test_parsers.py
    ├── test_embeddings.py
    └── test_rag.py
```

## Casos de Uso

### 1. Consulta Temporal

Encontrar normas vigentes em uma data específica:

```python
{
    "query": "requisitos de manutenção para aeronaves comerciais",
    "date": "2022-03-10"
}
```

### 2. Integração com Sistema Maior

Sistema de análise de voos integra com este módulo RAG:

```python
# Sistema maior coleta dados do voo
flight_data = get_flight_data("GOL1234", "2023-05-15")
weather_data = get_weather_data("SBGR", "2023-05-15T10:00:00Z")

# Consulta regulações relevantes
regulations = rag_api.search({
    "query": "normas sobre atrasos por condições meteorológicas",
    "date": "2023-05-15"
})

# Monta contexto unificado para LLM final
context = {
    "flight": flight_data,
    "weather": weather_data,
    "regulations": regulations["sources"]
}

# Gera resposta holística
answer = main_llm.generate(context, user_query)
```

### 3. Atualização de Normas

Script automático verifica novas normas diariamente:

```bash
# Cron job diário
0 2 * * * /path/to/venv/bin/python scripts/ingest_lexml.py --incremental
```

## Versionamento Temporal

O sistema mantém histórico completo de todas as versões de cada norma:

```python
# Cada chunk armazena metadados temporais
{
    "regulation_id": "lei-8666-art-42",
    "version": "2023-04-01",
    "version_number": 3,
    "effective_date": "2023-04-01T00:00:00Z",
    "expiry_date": null,  # null = ainda vigente
    "status": "active",   # active | superseded | draft
    "supersedes_version": "2022-01-15"
}
```

Consultas temporais retornam apenas versões vigentes na data especificada:

- Query com `date="2022-06-15"` → retorna versão 2
- Query com `date="2023-05-01"` → retorna versão 3

## Performance

### Ingestão
- **100k chunks:** ~2-3 horas (incluindo download, parsing, embedding)
- **Embedding:** ~100 textos/segundo (GPU, batch 32)

### Consulta
- **Llama 3.1 8B:** 3-6 segundos (end-to-end)
- **Llama 3.1 70B:** 6-15 segundos (end-to-end)
- **Vector Search:** 10-30 ms (500k vetores com índices)

### Recursos
- **RAM:** ~2-3 GB (Qdrant + API)
- **GPU VRAM:**
  - Legal-BERTimbau: ~1.2 GB
  - Llama 8B: ~10 GB
  - Llama 70B: ~80 GB (distribuído em 4-6 GPUs)

## Segurança

- ✅ **Autenticação:** API Key obrigatória (X-API-Key header)
- ✅ **Rate Limiting:** 100 req/min por IP
- ✅ **Input Validation:** Pydantic schemas com sanitização
- ✅ **Logging:** Todos os acessos registrados
- ✅ **CORS:** Configurável (restritivo por padrão)

Para produção, considere adicionar:
- HTTPS/TLS (certificados SSL)
- Firewall rules
- Network isolation
- Secrets management (Vault)

## Upgrade de Llama 8B → 70B

Trocar modelo é trivial:

```bash
# 1. Baixar modelo maior
ollama pull llama3.1:70b

# 2. Editar config.py
# Alterar: OLLAMA_MODEL = "llama3.1:70b"

# 3. Reiniciar API
# Pronto! Nenhuma outra mudança necessária
```

## Documentação Completa

Para detalhes técnicos completos, consulte:

📄 **documentation.tex** - Documento LaTeX com:
- Fundamentação teórica (RAG, Vector Databases, HNSW)
- Arquitetura detalhada (diagramas)
- Escolhas tecnológicas justificadas
- Versionamento temporal
- Pipeline completo
- API REST
- Estimativas de performance
- Casos de uso

Compile com:
```bash
pdflatex documentation.tex
```

Ou faça upload no [Overleaf](https://www.overleaf.com/).

## Troubleshooting

### Qdrant não conecta
```bash
# Verificar se container está rodando
docker ps | grep qdrant

# Ver logs
docker logs qdrant

# Reiniciar
docker-compose restart qdrant
```

### Ollama não responde
```bash
# Verificar status
ollama list

# Reiniciar serviço
sudo systemctl restart ollama

# Testar manualmente
ollama run llama3.1:8b "teste"
```

### Erro de GPU/CUDA
```bash
# Verificar GPUs disponíveis
nvidia-smi

# Verificar PyTorch detecta GPU
python -c "import torch; print(torch.cuda.is_available())"

# Se False, reinstalar PyTorch com CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Embeddings muito lentos
```bash
# Verificar se está usando GPU
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('rufimelo/Legal-BERTimbau-sts-large-ma-v3'); print(m.device)"

# Deve mostrar: cuda:0
# Se mostrar 'cpu', verificar instalação CUDA
```

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Trabalhos Futuros

- [ ] Hybrid Search (semântica + keyword)
- [ ] Fine-tuning em corpus de ICAs
- [ ] OCR para PDFs escaneados
- [ ] Interface web (Streamlit/Gradio)
- [ ] Avaliação sistemática (benchmark)
- [ ] Cache inteligente (Redis)
- [ ] Monitoramento (Prometheus + Grafana)

## Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

## Contato

Para questões, sugestões ou suporte:
- **Email:** contato@airdata.com.br
- **Issues:** [GitHub Issues](https://github.com/your-org/aviation-rag-system/issues)

## Citação

Se você usar este sistema em pesquisa acadêmica, por favor cite:

```bibtex
@software{aviation_rag_2024,
  title={Sistema RAG para Consulta Temporal de Normas de Aviação Brasileira},
  author={Projeto AirData},
  year={2024},
  url={https://github.com/your-org/aviation-rag-system}
}
```

---

**Projeto AirData** - Integrando dados de aviação brasileira com IA
