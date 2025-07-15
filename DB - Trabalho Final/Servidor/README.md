# SaveBox Servidor - Backend de Armazenamento Seguro

O servidor SaveBox é o backend responsável por gerenciar usuários, autenticação, armazenamento de arquivos e operações de rede.

## 🏗️ Arquitetura

O servidor implementa:
- **Servidor Multi-threaded**: Suporte simultâneo a múltiplos clientes
- **Banco de Dados SQLite**: Gerenciamento de usuários e metadados
- **Sistema de Arquivos**: Armazenamento organizado por usuário
- **Comunicação SSL**: Conexões criptografadas
- **API de Comandos**: Protocolo personalizado cliente-servidor

## 🗄️ Estrutura de Dados

### Sistema de Arquivos
```
storage/
└── [username]/
    ├── [arquivo_criptografado_1]
    └── [arquivo_criptografado_2]
```

## 🔧 Configuração

### Pré-requisitos
- Python 3.7 ou superior
- Dependências padrão do Python (socket, ssl, sqlite3, etc.)

### Certificados SSL
Gere os certificados SSL necessários:
```bash
# Gerar chave privada
openssl genrsa -out key.pem 2048

# Gerar certificado auto-assinado
openssl req -new -x509 -key key.pem -out cert.pem -days 365
```

### Configuração de Rede
No arquivo `servidor.py`, ajuste:
```python
HOST = 'localhost'    # Endereço do servidor
PORT = 65432          # Porta de escuta
BUFFER_SIZE = 4096    # Tamanho do buffer
```

## 🚀 Como Executar

### Execução Básica
```bash
python servidor.py
```

### Execução com Log Detalhado
```bash
python servidor.py --verbose
```

## 📡 Protocolo de Comunicação

### Comandos Suportados

#### Autenticação
- `AUTH|username|password`: Login de usuário
- `REGISTER|username|password`: Registro de novo usuário

#### Operações de Arquivo
- `LIST|path`: Listar arquivos em diretório
- `UPLOAD|path|size`: Upload de arquivo
- `DOWNLOAD|path`: Download de arquivo
- `DELETE|path`: Deletar arquivo/pasta

#### Operações de Pasta
- `CREATE_FOLDER|path`: Criar nova pasta
- `DOWNLOAD_FOLDER_AS_ZIP|path`: Download de pasta como ZIP
- `UPLOAD_ZIP_AS_FOLDER|path|size`: Upload de ZIP e extração

#### Estatísticas
- `GET_STATS`: Obter estatísticas do usuário

### Formato de Resposta
```
OK|dados_adicionais        # Sucesso
ERROR|mensagem_erro        # Erro
STATS|up_count|down_count|up_bytes|down_bytes  # Estatísticas
```

## 🔐 Segurança

### Autenticação
- **Hash de Senha**: SHA-256 com salt único por usuário
- **Salt Aleatório**: 32 bytes gerados aleatoriamente
- **Verificação**: Comparação segura de hashes

### Comunicação
- **SSL/TLS**: Todas as comunicações criptografadas
- **Certificados**: Validação de identidade do servidor

### Armazenamento
- **Isolamento**: Cada usuário tem diretório próprio
- **Validação**: Verificação de paths para evitar directory traversal
- **Logs**: Registro de todas as atividades
