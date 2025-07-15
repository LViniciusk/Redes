# SaveBox Relatórios - Dashboard de Uso e Estatísticas

O módulo de relatórios do SaveBox gera dashboards detalhados com estatísticas de uso, atividades dos usuários e métricas do sistema.

## 📊 Funcionalidades

### Dashboard Principal
- **Resumo Geral**: Estatísticas do sistema
- **Análise por Usuário**: Detalhamento individual de cada usuário
- **Atividades Recentes**: Log das operações mais recentes
- **Análise Temporal**: Tendências de uso por período


## 🔧 Instalação e Configuração

### Pré-requisitos
```bash
pip install pandas openpyxl
```

### Dependências
- `pandas`: Manipulação e análise de dados
- `openpyxl`: Geração de arquivos Excel avançados
- `sqlite3`: Conexão com banco de dados (built-in Python)

### Configuração de Banco
```python
DB_FILE = os.path.join("pasta/do/banco", "banco.db")
```

## 🚀 Como Executar

### Execução Simples
```bash
cd Relatórios
python relatorio.py
```

### Execução Programada
```bash
# Linux/Mac - Adicionar ao crontab
0 0 * * * /usr/bin/python3 /caminho/para/relatorio.py

# Windows - Task Scheduler
schtasks /create /tn "SaveBoxReport" /tr "python relatorio.py" /sc daily
```