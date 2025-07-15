# SaveBox Cliente - Interface Desktop

O cliente SaveBox é uma aplicação desktop desenvolvida em Python com Tkinter que oferece uma interface gráfica intuitiva para gerenciar arquivos na nuvem com criptografia end-to-end.

## 🎨 Interface

A interface do cliente oferece:
- **Login/Registro**: Tela inicial para autenticação
- **Navegador de Arquivos**: Similar ao explorador de arquivos do Windows
- **Barra de Progresso**: Acompanhamento de uploads/downloads
- **Menu Contextual**: Clique direito para opções rápidas
- **Painel de Controle**: Botões para ações principais

## 🔧 Instalação

### Pré-requisitos
- Python 3.7 ou superior
- Pip (gerenciador de pacotes Python)

### Dependências
```bash
pip install -r requirements.txt
```

#### Pacotes incluídos:
- `cryptography==45.0.5`: Biblioteca de criptografia
- `cffi==1.17.1`: Interface C para Python
- `pycparser==2.22`: Parser C para Python

## 🚀 Como Executar

### Execução Padrão
```bash
python cliente.py
```

## ⚙️ Configuração

### Conexão com Servidor
Na tela de login, configure:
- **Host**: Endereço do servidor (padrão: localhost)
- **Porta**: Porta do servidor (padrão: 65432)

### Certificados SSL
O arquivo `cert.pem` deve estar presente na pasta do cliente para comunicação segura.

## 📋 Funcionalidades

### Autenticação
- **Login**: Conecta com credenciais existentes
- **Registro**: Cria nova conta de usuário
- **Logout**: Desconecta do servidor

### Gerenciamento de Arquivos
- **Upload**: Envio de arquivos individuais
- **Download**: Baixar arquivos do servidor
- **Navegação**: Explorar estrutura de pastas
- **Criação de Pastas**: Organizar arquivos
- **Exclusão**: Remover arquivos e pastas

### Funcionalidades Avançadas
- **Upload de ZIP**: Converte arquivo ZIP em estrutura de pastas
- **Download de Pasta**: Baixa pasta completa como arquivo ZIP
- **Ordenação**: Organizar arquivos por nome, tamanho ou data
- **Atualização**: Sincronizar lista de arquivos

### Estatísticas
- **Meus Dados**: Visualizar estatísticas pessoais de uso
- **Histórico**: Contadores de upload/download
- **Volume de Dados**: Total de bytes transferidos

## 🎯 Como Usar

### Primeiro Acesso
1. Execute `cliente.py`
2. Configure host e porta do servidor
3. Clique em "Registrar" para criar conta
4. Faça login com suas credenciais

### Gerenciando Arquivos
1. **Upload**: Clique em "Fazer Upload" ou clique direito → "Novo Arquivo"
2. **Download**: Selecione arquivo → "Fazer Download" ou clique direito
3. **Pasta**: Clique direito → "Nova Pasta" ou "Criar pasta de um .zip"
4. **Navegação**: Duplo clique em pastas para entrar

### Menus Contextuais
- **Arquivo**: Download, Deletar
- **Pasta**: Download como ZIP, Deletar
- **Área Vazia**: Novo arquivo, Nova pasta, Upload ZIP, Download pasta atual

## 🔐 Segurança

### Criptografia Local
- Todos os arquivos são criptografados localmente antes do upload
- Nomes de arquivos também são criptografados
- Chave derivada da senha do usuário com PBKDF2

### Comunicação Segura
- Conexão SSL/TLS com o servidor
- Verificação de certificado
- Transmissão criptografada de dados

## 🎨 Ícones e Interface

O cliente inclui ícones para diferentes tipos de arquivo:
- 📁 `folder.png`: Pastas
- 📄 `text.png`: Arquivos de texto
- 📊 `pdf.png`: Documentos PDF
- 🔒 `enc.png`: Arquivos criptografados
- 🖼️ `image.png`: Imagens
- 🎬 `video.png`: Vídeos
- 🎵 `audio.png`: Áudio
- 📦 `zip.png`: Arquivos compactados
- 💻 `code.png`: Código fonte
- 📋 `file.png`: Arquivos genéricos
- 🔑 `pem.png`: Certificados

## 🐛 Solução de Problemas

### Erro de Conexão
- Verifique se o servidor está executando
- Confirme host e porta corretos
- Verifique firewall e antivírus

### Erro de Certificado
- Certifique-se que `cert.pem` está presente
- Arquivo deve ser o mesmo usado pelo servidor

### Erro de Login
- Verifique credenciais
- Teste registro de nova conta
- Confirme conexão com servidor

### Performance
- Para arquivos grandes, aguarde conclusão do upload/download
- Use pasta ZIP para transferir múltiplos arquivos
- Monitore progresso na barra inferior

## 🔧 Desenvolvimento

### Estrutura do Código
- `CloudClient`: Classe principal da aplicação
- `encrypt_*`/`decrypt_*`: Funções de criptografia
- `resource_path()`: Localização de recursos
- Threads separadas para operações de rede

### Personalização
- Modifique `HOST` e `PORT` para diferentes servidores
- Ajuste `BUFFER_SIZE` para otimizar transferência
- Personalize interface modificando layout Tkinter

## 📄 Arquivos Importantes

- `cliente.py`: Código principal da aplicação
- `requirements.txt`: Dependências Python
- `cert.pem`: Certificado SSL para conexão segura
- `icons/`: Pasta com ícones da interface
