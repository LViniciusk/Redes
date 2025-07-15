# SaveBox - Sistema de Armazenamento Seguro em Nuvem

SaveBox é um sistema de armazenamento de arquivos na nuvem com criptografia end-to-end.

## 🚀 Características Principais

- **Criptografia End-to-End**: Todos os arquivos são criptografados localmente antes do upload
- **Interface Gráfica**: Cliente desktop com Tkinter
- **Gerenciamento de Pastas**: Criação, navegação e download de pastas como ZIP
- **Upload de ZIP**: Extração automática de arquivos ZIP em pastas estruturadas
- **Autenticação Segura**: Sistema de login com hash e salt
- **Relatórios de Uso**: Dashboard em Excel com estatísticas detalhadas
- **Conexão SSL/TLS**: Comunicação segura entre cliente e servidor

## 📁 Estrutura do Projeto

```
ProjetoFInalRedesTeste/
├── Cliente/           # Aplicação cliente desktop
├── Servidor/          # Servidor backend
├── Relatórios/        # Sistema de relatórios
└── README.md          # Este arquivo
```

## 🛠️ Tecnologias Utilizadas

- **Python 3**: Linguagem principal
- **Tkinter**: Interface gráfica do cliente
- **SQLite**: Banco de dados do servidor
- **Cryptography**: Biblioteca de criptografia
- **SSL/TLS**: Certificados para comunicação segura
- **Pandas/OpenPyXL**: Geração de relatórios Excel

## 📋 Pré-requisitos

- Python 3.7 ou superior
- Dependências listadas em `Cliente/requirements.txt`
- Certificados SSL (cert.pem e key.pem) para o servidor

## 🔧 Instalação e Configuração

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd "DB - Trabalho Final"
```

### 2. Configure o servidor
```bash
cd Servidor
python servidor.py
```

### 3. Configure o cliente
```bash
cd Cliente
pip install -r requirements.txt
python cliente.py
```

### 4. Gerar relatórios (opcional)
```bash
cd Relatórios
python relatorio.py
```

## 🔐 Segurança

O SaveBox implementa múltiplas camadas de segurança:

- **Criptografia AES-256-GCM**: Para arquivos e nomes de arquivos
- **PBKDF2**: Derivação de chaves com 100.000 iterações
- **SSL/TLS**: Comunicação criptografada
- **Autenticação**: Sistema de login com senha hash + salt

## 📊 Funcionalidades

### Cliente
- Login/Registro de usuários
- Upload/Download de arquivos
- Navegação em pastas
- Criação de pastas
- Upload de ZIP como estrutura de pastas
- Download de pastas como ZIP
- Visualização de estatísticas pessoais

### Servidor
- Gerenciamento de usuários
- Armazenamento seguro de arquivos
- Log de atividades
- API para operações de arquivo

### Relatórios
- Dashboard em Excel
- Estatísticas de uso por usuário
- Análise de atividades
- Métricas de armazenamento

## 🎯 Como Usar

1. **Inicie o servidor**: Execute `servidor.py`
2. **Abra o cliente**: Execute `cliente.py`
3. **Faça login/registro**: Use a interface gráfica
4. **Gerencie arquivos**: Upload, download, organize pastas
5. **Visualize relatórios**: Execute `relatorio.py` quando necessário

## 📄 Licença

Este projeto é desenvolvido para fins educacionais como projeto final de redes.
