import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join("servidor/database", "database.db")
OUTPUT_FILE = f"relatorio_de_uso_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

def format_bytes(size):
    try:
        size = float(size)
    except (ValueError, TypeError):
        return "0 B"
        
    if size == 0: 
        return "0 B"
        
    power, n = 1024, 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < len(power_labels) - 1:
        size /= power; n += 1
    return f"{size:.2f} {power_labels[n]}"

def create_dashboard_spreadsheet():
    if not os.path.exists(DB_FILE):
        print(f"Erro: Arquivo de banco de dados não encontrado em '{DB_FILE}'")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        print("Lendo dados do banco de dados...")
        df_log = pd.read_sql_query("SELECT user_login, activity_type, file_size_bytes, activity_timestamp FROM activity_log", conn)
        conn.close()

        if df_log.empty:
            print("Nenhuma atividade registrada para gerar o dashboard.")
            return
            
        df_log['activity_timestamp'] = pd.to_datetime(df_log['activity_timestamp'])
        
        print("Processando dados para o dashboard...")
        
        now = datetime.now()
        
        total_uploads = df_log[df_log['activity_type'] == 'UPLOAD'].shape[0]
        total_downloads = df_log[df_log['activity_type'] == 'DOWNLOAD'].shape[0]
        total_bytes_up = df_log[df_log['activity_type'] == 'UPLOAD']['file_size_bytes'].sum()
        total_bytes_down = df_log[df_log['activity_type'] == 'DOWNLOAD']['file_size_bytes'].sum()
        
        last_24h = df_log[df_log['activity_timestamp'] >= now - timedelta(days=1)]
        uploads_24h_count = last_24h[last_24h['activity_type'] == 'UPLOAD'].shape[0]
        downloads_24h_count = last_24h[last_24h['activity_type'] == 'DOWNLOAD'].shape[0]
        bytes_up_24h = last_24h[last_24h['activity_type'] == 'UPLOAD']['file_size_bytes'].sum()
        bytes_down_24h = last_24h[last_24h['activity_type'] == 'DOWNLOAD']['file_size_bytes'].sum()

        last_30d = df_log[df_log['activity_timestamp'] >= now - timedelta(days=30)]
        uploads_30d_count = last_30d[last_30d['activity_type'] == 'UPLOAD'].shape[0]
        downloads_30d_count = last_30d[last_30d['activity_type'] == 'DOWNLOAD'].shape[0]
        bytes_up_30d = last_30d[last_30d['activity_type'] == 'UPLOAD']['file_size_bytes'].sum()
        bytes_down_30d = last_30d[last_30d['activity_type'] == 'DOWNLOAD']['file_size_bytes'].sum()

        summary_data = {
            'Métrica': [
                "Total de Transações de Upload", "Total de Transações de Download",
                "Volume Total de Upload", "Volume Total de Download",
                "Uploads (Últimas 24h)", "Downloads (Últimas 24h)",
                "Uploads (Últimos 30 dias)", "Downloads (Últimos 30 dias)"
            ],
            'Valor': [
                f"{total_uploads} arquivos", f"{total_downloads} arquivos",
                format_bytes(total_bytes_up), format_bytes(total_bytes_down),
                f"{uploads_24h_count} ({format_bytes(bytes_up_24h)})", f"{downloads_24h_count} ({format_bytes(bytes_down_24h)})",
                f"{uploads_30d_count} ({format_bytes(bytes_up_30d)})", f"{downloads_30d_count} ({format_bytes(bytes_down_30d)})"
            ]
        }
        df_summary = pd.DataFrame(summary_data)

        # Criar resumo por usuário usando agg() para evitar warnings
        upload_stats = df_log[df_log['activity_type'] == 'UPLOAD'].groupby('user_login').agg({
            'file_size_bytes': ['count', 'sum']
        }).fillna(0)
        download_stats = df_log[df_log['activity_type'] == 'DOWNLOAD'].groupby('user_login').agg({
            'file_size_bytes': ['count', 'sum']
        }).fillna(0)
        
        # Obter todos os usuários únicos
        all_users = df_log['user_login'].unique()
        
        user_summary_data = []
        for user in all_users:
            upload_count = upload_stats.loc[user, ('file_size_bytes', 'count')] if user in upload_stats.index else 0
            upload_bytes = upload_stats.loc[user, ('file_size_bytes', 'sum')] if user in upload_stats.index else 0
            download_count = download_stats.loc[user, ('file_size_bytes', 'count')] if user in download_stats.index else 0
            download_bytes = download_stats.loc[user, ('file_size_bytes', 'sum')] if user in download_stats.index else 0
            
            user_summary_data.append({
                'Usuário': user,
                'Uploads (Qtd)': int(upload_count),
                'Uploads (Vol)': format_bytes(upload_bytes),
                'Downloads (Qtd)': int(download_count),
                'Downloads (Vol)': format_bytes(download_bytes)
            })
        
        user_summary = pd.DataFrame(user_summary_data)
        
        df_recent = df_log.sort_values(by='activity_timestamp', ascending=False).head(10)
        df_recent['Tamanho'] = df_recent['file_size_bytes'].apply(format_bytes)
        df_recent_report = df_recent[['activity_timestamp', 'user_login', 'activity_type', 'Tamanho']].rename(columns={
            'activity_timestamp': 'Data e Hora', 'user_login': 'Usuário', 'activity_type': 'Atividade'
        })
        df_recent_report['Data e Hora'] = df_recent_report['Data e Hora'].dt.strftime('%d/%m/%Y %H:%M')

        print(f"Salvando dashboard como '{OUTPUT_FILE}'...")
        with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Dashboard')

            title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
            subtitle_format = workbook.add_format({'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter', 'bottom': 1, 'bg_color': '#F2F2F2'})
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#DDEBF7'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
            left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
            
            worksheet.merge_range('A1:L1', f"RELATÓRIO DE USO - {datetime.now().strftime('%d/%m/%Y %H:%M')}", title_format)
            worksheet.set_row(0, 30)

            def write_table(df, start_row, start_col, title):
                num_cols = len(df.columns)
                worksheet.merge_range(start_row, start_col, start_row, start_col + num_cols - 1, title, subtitle_format)
                
                for c_idx, col_name in enumerate(df.columns):
                    worksheet.write(start_row + 1, start_col + c_idx, col_name, header_format)
                
                for r_idx, row in enumerate(df.itertuples(index=False), start=start_row + 2):
                    for c_idx, value in enumerate(row):
                        cell_format = left_format if c_idx == 0 else center_format
                        worksheet.write(r_idx, start_col + c_idx, value, cell_format)

            write_table(df_summary, 3, 0, "RESUMO GERAL DO SISTEMA")
            worksheet.set_column(0, 0, 35)
            worksheet.set_column(1, 1, 25)

            write_table(user_summary, 3, 3, "ATIVIDADE DETALHADA POR USUÁRIO")
            worksheet.set_column(3, 3, 25)
            worksheet.set_column(4, 7, 18)

            write_table(df_recent_report, 3, 9, "ÚLTIMAS 10 ATIVIDADES")
            worksheet.set_column(9, 12, 20)
            
        print(f"\nDashboard em planilha gerado com sucesso!")
        print(f"O arquivo '{OUTPUT_FILE}' foi salvo nesta pasta.")

    except Exception as e:
        print(f"Ocorreu um erro ao gerar o relatório: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_dashboard_spreadsheet()
