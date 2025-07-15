import socket
import threading
import os
import sqlite3
import hashlib
import ssl
import json
import zipfile
import io
import time
import traceback

HOST = 'localhost'
PORT = 65432
STORAGE_DIR = "storage"
DB_DIR = "database"
DB_FILE = "./database/database.db"
BUFFER_SIZE = 4096

class DatabaseManager:
    def __init__(self, db_file):
        db_dir = os.path.dirname(db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.create_user_table()
        self.create_metadata_table()


    def create_user_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt BLOB NOT NULL,
            upload_count INTEGER NOT NULL DEFAULT 0,
            download_count INTEGER NOT NULL DEFAULT 0,
            total_bytes_uploaded INTEGER NOT NULL DEFAULT 0,
            total_bytes_downloaded INTEGER NOT NULL DEFAULT 0
        );
        """
        cursor = self.conn.cursor(); cursor.execute(sql); self.conn.commit()


    def create_metadata_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_login TEXT NOT NULL,
            parent_path_logical TEXT NOT NULL,
            logical_name TEXT NOT NULL,
            physical_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            created_date REAL DEFAULT (julianday('now')),
            UNIQUE(user_login, parent_path_logical, logical_name)
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()


    def add_metadata(self, login, parent_path_logical, logical_name, physical_name, item_type):
        sql = "INSERT OR IGNORE INTO metadata (user_login, parent_path_logical, logical_name, physical_name, item_type) VALUES (?, ?, ?, ?, ?)"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login, parent_path_logical, logical_name, physical_name, item_type))
        self.conn.commit()


    def get_metadata_item(self, login, parent_path_logical, logical_name):
        sql = "SELECT physical_name, item_type FROM metadata WHERE user_login = ? AND parent_path_logical = ? AND logical_name = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login, parent_path_logical, logical_name))
        return cursor.fetchone()
    

    def get_physicals_to_delete(self, login, full_logical_path):
        cursor = self.conn.cursor()
        path = full_logical_path.replace('\\', '/').strip('/')
        
        parent_path = os.path.dirname(path)
        logical_name = os.path.basename(path)
        
        sql_main = "SELECT physical_name, item_type FROM metadata WHERE user_login = ? AND parent_path_logical = ? AND logical_name = ?"
        cursor.execute(sql_main, (login, parent_path, logical_name))
        main_item = cursor.fetchone()

        if not main_item:
            return None, [] 

        item_type = main_item[1]
        physicals_to_delete = [main_item[0]]

        if item_type == 'folder':       
            path_for_like = path.rstrip('/') + '/%'
            sql_children = "SELECT physical_name FROM metadata WHERE user_login = ? AND (parent_path_logical = ? OR parent_path_logical LIKE ?)"
            cursor.execute(sql_children, (login, path, path_for_like))
            children_physicals = [row[0] for row in cursor.fetchall()]
            physicals_to_delete.extend(children_physicals)

        return item_type, physicals_to_delete


    def delete_metadata_recursive(self, login, full_logical_path):
        cursor = self.conn.cursor()
        path = full_logical_path.replace('\\', '/').strip('/')
        
        cursor.execute("DELETE FROM metadata WHERE user_login = ? AND parent_path_logical LIKE ?", (login, path + '/%'))
        
        parent_path = os.path.dirname(path)
        logical_name = os.path.basename(path)
        cursor.execute("DELETE FROM metadata WHERE user_login = ? AND parent_path_logical = ? AND logical_name = ?", (login, parent_path, logical_name))
        
        self.conn.commit()


    def list_path(self, login, parent_path_logical):
        sql = "SELECT logical_name, physical_name, item_type, created_date FROM metadata WHERE user_login = ? AND parent_path_logical = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login, parent_path_logical))
        return cursor.fetchall()


    def _hash_password(self, password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    

    def register_user(self, login, password):
        password_hash = self._hash_password(password)
        salt = os.urandom(16)
        sql = "INSERT INTO usuarios (login, password_hash, password_salt) VALUES (?, ?, ?)"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (login, password_hash, salt))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    
    def get_user_salt(self, login):
        sql = "SELECT password_salt FROM usuarios WHERE login = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return None


    def check_credentials(self, login, password):
        password_hash = self._hash_password(password)
        sql = "SELECT id FROM usuarios WHERE login = ? AND password_hash = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login, password_hash))
        return cursor.fetchone() is not None
    
    
    def log_upload(self, login, filesize):
        sql = "UPDATE usuarios SET upload_count = upload_count + 1, total_bytes_uploaded = total_bytes_uploaded + ? WHERE login = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (filesize, login))
        self.conn.commit()

    
    def log_download(self, login, filesize):
        sql = "UPDATE usuarios SET download_count = download_count + 1, total_bytes_downloaded = total_bytes_downloaded + ? WHERE login = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (filesize, login))
        self.conn.commit()

    
    def get_user_stats(self, login):
        sql = "SELECT upload_count, download_count, total_bytes_uploaded, total_bytes_downloaded FROM usuarios WHERE login = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login,))
        return cursor.fetchone()


    def update_modification_date(self, login, parent_path_logical, logical_name):
        sql = "UPDATE metadata SET created_date = julianday('now') WHERE user_login = ? AND parent_path_logical = ? AND logical_name = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, (login, parent_path_logical, logical_name))
        self.conn.commit()
    

    def update_parent_folders_dates(self, login, child_path_logical):
        path = child_path_logical.replace('\\', '/').strip('/')
        
        if not path:
            return
            
        path_parts = path.split('/')
        
        current_path = ""
        for i, part in enumerate(path_parts[:-1]):
            if i == 0:
                parent_path = ""
                logical_name = part
            else:
                parent_path = current_path
                logical_name = part
            
            self.update_modification_date(login, parent_path, logical_name)
            
            if current_path:
                current_path += "/" + part
            else:
                current_path = part


    def get_all_files_in_folder_recursive(self, login, folder_path_logical):
        cursor = self.conn.cursor()
        
        folder_path = folder_path_logical.replace('\\', '/').strip('/')
        
        if not folder_path:
            sql = "SELECT parent_path_logical, logical_name, physical_name FROM metadata WHERE user_login = ? AND item_type = 'file'"
            cursor.execute(sql, (login,))
        else:
            like_pattern = folder_path + '/%'
            sql = """SELECT parent_path_logical, logical_name, physical_name 
                     FROM metadata 
                     WHERE user_login = ? AND item_type = 'file' 
                     AND (parent_path_logical = ? OR parent_path_logical LIKE ?)"""
            cursor.execute(sql, (login, folder_path, like_pattern))
        
        return cursor.fetchall()


    def get_all_folders_in_folder_recursive(self, login, folder_path_logical):
        cursor = self.conn.cursor()
        
        folder_path = folder_path_logical.replace('\\', '/').strip('/')
        
        if not folder_path:
            sql = "SELECT parent_path_logical, logical_name FROM metadata WHERE user_login = ? AND item_type = 'folder'"
            cursor.execute(sql, (login,))
        else:
            like_pattern = folder_path + '/%'
            sql = """SELECT parent_path_logical, logical_name 
                     FROM metadata 
                     WHERE user_login = ? AND item_type = 'folder' 
                     AND (parent_path_logical = ? OR parent_path_logical LIKE ?)"""
            cursor.execute(sql, (login, folder_path, like_pattern))
        
        return cursor.fetchall()

def get_safe_path(base_dir, client_path):
    client_path = client_path.lstrip('/\\')
    full_path = os.path.join(base_dir, client_path)
    real_path = os.path.abspath(full_path)
    if os.path.commonprefix([real_path, os.path.abspath(base_dir)]) != os.path.abspath(base_dir):
        return None
        
    return real_path


db_manager = DatabaseManager(DB_FILE)


def setup_storage():
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)


def handle_client(secure_conn, addr):
    print(f"[NOVA CONEXÃO] {addr} conectado.")
    authenticated_user = None
    try:
        while True:
            data = secure_conn.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                break
            
            parts = data.split('|')
            command = parts[0]

            # --- Bloco de Autenticação e Registro ---
            if command == "AUTH" or command == "REGISTER":
                login, password = parts[1], parts[2]

                if command == "AUTH":
                    if db_manager.check_credentials(login, password):
                        authenticated_user = login
                        user_base_folder = os.path.join(STORAGE_DIR, authenticated_user)
                        os.makedirs(user_base_folder, exist_ok=True)
                        
                        salt = db_manager.get_user_salt(login)
                        
                        if salt:
                            salt_hex = salt.hex()
                            secure_conn.send(f"OK|{salt_hex}".encode('utf-8'))
                            print(f"[AUTH] Usuário '{authenticated_user}' autenticado de {addr}.")
                        else:
                            secure_conn.send("ERRO|Falha ao obter dados de segurança do usuário.".encode('utf-8'))
                    else:
                        secure_conn.send("ERRO|usuario não existe".encode('utf-8'))

                elif command == "REGISTER":
                    if db_manager.register_user(login, password):
                        secure_conn.send("OK|Registrado com sucesso!".encode('utf-8'))

                    else:
                        secure_conn.send("ERRO|Usuário já existe.".encode('utf-8'))
            
            # --- Bloco de Comandos Autenticados ---
            elif authenticated_user:
                user_base_folder = os.path.join(STORAGE_DIR, authenticated_user)

                if command == "CREATE_FOLDER":
                    encrypted_relative_path = parts[1]
                    parent_path_logical = os.path.dirname(encrypted_relative_path).replace('\\', '/')
                    logical_name = os.path.basename(encrypted_relative_path)
                    physical_name = hashlib.sha1(logical_name.encode()).hexdigest() + "_folder"
                    
                    db_manager.add_metadata(authenticated_user, parent_path_logical, logical_name, physical_name, 'folder')
                    
                    db_manager.update_parent_folders_dates(authenticated_user, encrypted_relative_path)
                    
                    secure_conn.send("OK|Pasta criada.".encode('utf-8'))


                elif command == "LIST":
                    # LIST|caminho/logico/relativo
                    encrypted_relative_path = parts[1].replace('\\', '/')
                    
                    items_in_db = db_manager.list_path(authenticated_user, encrypted_relative_path)
                    
                    file_details = []
                    for logical_name, physical_name, item_type, created_date in items_in_db:
                        
                        full_physical_path = get_safe_path(user_base_folder, physical_name)
                        
                        size, date = 0, 0
                        if full_physical_path and os.path.exists(full_physical_path):
                            stats = os.stat(full_physical_path)
                            size, date = stats.st_size, stats.st_mtime
                        else:
                            julian_days = created_date if created_date else 0
                            if julian_days > 0:
                                date = (julian_days - 2440587.5) * 86400
                            else:
                                date = time.time()
                        
                        file_details.append({
                            'name': logical_name,
                            'size': size,
                            'date': date,
                            'type': item_type
                        })
                    
                    response_json = json.dumps(file_details)
                    header = f"{len(response_json):<10}".encode('utf-8')
                    secure_conn.sendall(header + response_json.encode('utf-8'))

                elif command == "UPLOAD":
                    # UPLOAD|caminho/criptografado/arquivo_cripto.enc|tamanho
                    encrypted_relative_path, filesize = parts[1], int(parts[2])
                    parent_path_logical = os.path.dirname(encrypted_relative_path).replace('\\', '/')
                    logical_name = os.path.basename(encrypted_relative_path)
                    physical_name = hashlib.sha1(logical_name.encode()).hexdigest()
                    
                    full_physical_path = get_safe_path(user_base_folder, physical_name)
                    
                    secure_conn.send("OK".encode('utf-8'))
                    
                    bytes_received = 0
                    try:
                        with open(full_physical_path, 'wb') as f:
                            while bytes_received < filesize:
                                chunk = secure_conn.recv(BUFFER_SIZE)
                                if not chunk: break
                                f.write(chunk)
                                bytes_received += len(chunk)
                        
                        if bytes_received < filesize:
                            os.remove(full_physical_path)
                            secure_conn.send("ERRO|Upload incompleto.".encode('utf-8'))
                        else:
                            db_manager.add_metadata(authenticated_user, parent_path_logical, logical_name, physical_name, 'file')
                            db_manager.log_upload(authenticated_user, bytes_received)
                            
                            db_manager.update_parent_folders_dates(authenticated_user, encrypted_relative_path)
                            
                            secure_conn.send("OK|UPLOAD_SUCCESS".encode('utf-8'))
                            print(f"[UPLOAD] Arquivo '{logical_name}' salvo em '{full_physical_path}'.")
                            
                    except Exception as e:
                        print(f"Erro durante o upload para {full_physical_path}: {e}")
                        if os.path.exists(full_physical_path): os.remove(full_physical_path)
                        secure_conn.send(f"ERRO|{e}".encode('utf-8'))

                elif command == "DOWNLOAD":
                    # DOWNLOAD|caminho/relativo/arquivo.txt
                    encrypted_relative_path = parts[1]
                    parent_path_logical = os.path.dirname(encrypted_relative_path).replace('\\', '/')
                    logical_name = os.path.basename(encrypted_relative_path)

                    item_metadata = db_manager.get_metadata_item(authenticated_user, parent_path_logical, logical_name)
                    if not item_metadata or item_metadata[1] != 'file':
                        secure_conn.send("ERRO|Arquivo não encontrado.".encode('utf-8'))
                        continue

                    physical_name = item_metadata[0]
                    full_physical_path = get_safe_path(user_base_folder, physical_name)

                    if not full_physical_path or not os.path.isfile(full_physical_path):
                        secure_conn.send("ERRO|Arquivo físico não encontrado no disco.".encode('utf-8'))
                        continue
                    
                    try:
                        filesize = os.path.getsize(full_physical_path)
                        secure_conn.send(f"OK|{filesize}".encode('utf-8'))
                        secure_conn.recv(BUFFER_SIZE)

                        with open(full_physical_path, 'rb') as f:
                            while True:
                                chunk = f.read(BUFFER_SIZE)
                                if not chunk: break
                                secure_conn.sendall(chunk)
                        
                        db_manager.log_download(authenticated_user, filesize)
                        print(f"[DOWNLOAD] Arquivo em '{encrypted_relative_path}' enviado para '{authenticated_user}'.")
                    except Exception as e:
                        print(f"ERRO ao enviar o arquivo {full_physical_path}: {e}")

                elif command == "DOWNLOAD_FOLDER_AS_ZIP":
                    # DOWNLOAD_FOLDER_AS_ZIP|caminho/relativo/da/pasta
                    relative_path = parts[1]
                    

                    if relative_path:
                        parent_path_logical = os.path.dirname(relative_path).replace('\\', '/')
                        logical_name = os.path.basename(relative_path)
                        folder_metadata = db_manager.get_metadata_item(authenticated_user, parent_path_logical, logical_name)
                        
                        if not folder_metadata or folder_metadata[1] != 'folder':
                            secure_conn.send("ERRO|Pasta não encontrada.".encode('utf-8'))
                            continue
                    
                    files_in_folder = db_manager.get_all_files_in_folder_recursive(authenticated_user, relative_path)
                    folders_in_folder = db_manager.get_all_folders_in_folder_recursive(authenticated_user, relative_path)
                    
                    if not files_in_folder and not folders_in_folder:
                        secure_conn.send("ERRO|Pasta vazia.".encode('utf-8'))
                        continue

                    memory_zip = io.BytesIO()
                    total_size = 0

                    try:
                        with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for parent_path_logical, logical_name in folders_in_folder:
                                if parent_path_logical:
                                    full_logical_path = parent_path_logical + '/' + logical_name
                                else:
                                    full_logical_path = logical_name
                                
                                if relative_path:
                                    if full_logical_path.startswith(relative_path + '/'):
                                        archive_name = full_logical_path[len(relative_path) + 1:] + '/'
                                    elif full_logical_path == relative_path:
                                        continue 
                                    else:
                                        archive_name = logical_name + '/'
                                else:
                                    archive_name = full_logical_path + '/'
                                
                                zf.writestr(archive_name, b'')
                            
                            for parent_path_logical, logical_name, physical_name in files_in_folder:
                                if parent_path_logical:
                                    full_logical_path = parent_path_logical + '/' + logical_name
                                else:
                                    full_logical_path = logical_name
                                
                                full_physical_path = get_safe_path(user_base_folder, physical_name)
                                
                                if full_physical_path and os.path.isfile(full_physical_path):
                                    if relative_path:
                                        if full_logical_path.startswith(relative_path + '/'):
                                            archive_name = full_logical_path[len(relative_path) + 1:]
                                        else:
                                            archive_name = logical_name
                                    else:
                                        archive_name = full_logical_path
                                    
                                    zf.write(full_physical_path, arcname=archive_name)
                                    total_size += os.path.getsize(full_physical_path)

                        zip_size = memory_zip.getbuffer().nbytes
                        secure_conn.send(f"OK|{zip_size}".encode('utf-8'))
                        secure_conn.recv(BUFFER_SIZE)

                        memory_zip.seek(0)

                        while True:
                            chunk = memory_zip.read(BUFFER_SIZE)
                            if not chunk:
                                break
                            secure_conn.sendall(chunk)

                        db_manager.log_download(authenticated_user, total_size)
                        print(f"[ZIP] Pasta '{relative_path}' compactada e enviada para '{authenticated_user}'. Tamanho: {zip_size} bytes.")
                        
                    except Exception as e:
                        print(f"ERRO ao criar ZIP da pasta {relative_path}: {e}")
                        secure_conn.send(f"ERRO|Falha ao criar arquivo ZIP: {e}".encode('utf-8'))
                
                elif command == "DELETE":
                    # DELETE|caminho/relativo/criptografado/do_item
                    encrypted_relative_path = parts[1]

                    item_type, physical_names_to_delete = db_manager.get_physicals_to_delete(authenticated_user, encrypted_relative_path)

                    if item_type is None:
                        secure_conn.send("ERRO|Item não encontrado.".encode('utf-8'))
                        continue
                    
                    try:
                        for physical_name in physical_names_to_delete:
                            item_to_delete_path = get_safe_path(user_base_folder, physical_name)
                            
                            if item_to_delete_path and os.path.exists(item_to_delete_path):
                                item_name = os.path.basename(item_to_delete_path)
                                if os.path.isfile(item_to_delete_path):
                                    os.remove(item_to_delete_path)
                                    print(f"[DELETE] Item '{item_name}' foi deletado por '{authenticated_user}'.")
                        
                        db_manager.delete_metadata_recursive(authenticated_user, encrypted_relative_path)
                        
                        db_manager.update_parent_folders_dates(authenticated_user, encrypted_relative_path)
                        
                        secure_conn.send("OK|Item(s) deletado(s) com sucesso.".encode('utf-8'))
                        

                    except Exception as e:
                        print(f"ERRO ao deletar itens físicos: {e}")
                        secure_conn.send("ERRO|Falha ao deletar o item no servidor.".encode('utf-8'))

                elif command == "GET_STATS":
                    stats = db_manager.get_user_stats(authenticated_user)

                    if stats:
                        response = f"STATS|{stats[0]}|{stats[1]}|{stats[2]}|{stats[3]}"
                        secure_conn.send(response.encode('utf-8'))

                    else:
                        secure_conn.send("ERRO|Não foi possível obter estatísticas.".encode('utf-8'))

                elif command == "UPLOAD_ZIP_AS_FOLDER":
                    # UPLOAD_ZIP_AS_FOLDER|caminho_pasta_raiz_criptografado|tamanho_zip
                    encrypted_folder_path, filesize = parts[1], int(parts[2])
                    
                    parent_path_logical = os.path.dirname(encrypted_folder_path).replace('\\', '/')
                    logical_folder_name = os.path.basename(encrypted_folder_path)
                    physical_folder_name = hashlib.sha1(logical_folder_name.encode()).hexdigest() + "_folder"
                    
                    db_manager.add_metadata(authenticated_user, parent_path_logical, logical_folder_name, physical_folder_name, 'folder')
                    
                    secure_conn.send("OK".encode('utf-8'))
                    
                    bytes_received = 0
                    zip_content = io.BytesIO()
                    
                    try:
                        while bytes_received < filesize:
                            chunk = secure_conn.recv(min(filesize - bytes_received, BUFFER_SIZE))
                            if not chunk: 
                                break
                            zip_content.write(chunk)
                            bytes_received += len(chunk)
                        
                        if bytes_received < filesize:
                            secure_conn.send("ERRO|Upload do .zip incompleto.".encode('utf-8'))
                            continue
                        
                        zip_content.seek(0)
                        
                        with zipfile.ZipFile(zip_content, 'r') as zf:
                            for item_info in zf.infolist():
                                archive_path = item_info.filename.replace('\\', '/').rstrip('/')
                                if not archive_path:
                                    continue
                                
                                if item_info.is_dir():
                                    full_logical_path = os.path.join(encrypted_folder_path, archive_path).replace('\\', '/')
                                    parent_logical = os.path.dirname(full_logical_path)
                                    folder_logical_name = os.path.basename(full_logical_path)
                                    physical_name = hashlib.sha1(folder_logical_name.encode()).hexdigest() + "_folder"
                                    
                                    db_manager.add_metadata(authenticated_user, parent_logical, folder_logical_name, physical_name, 'folder')
                                else:

                                    full_logical_path = os.path.join(encrypted_folder_path, archive_path).replace('\\', '/')
                                    parent_logical = os.path.dirname(full_logical_path)
                                    file_logical_name = os.path.basename(full_logical_path)
                                    physical_name = hashlib.sha1(file_logical_name.encode()).hexdigest()
                                    
                                    full_physical_path = get_safe_path(user_base_folder, physical_name)
                                    encrypted_file_content = zf.read(item_info.filename)
                                    
                                    with open(full_physical_path, 'wb') as f:
                                        f.write(encrypted_file_content)
                                    
                                    db_manager.add_metadata(authenticated_user, parent_logical, file_logical_name, physical_name, 'file')
                        
                        db_manager.log_upload(authenticated_user, bytes_received)
                        db_manager.update_parent_folders_dates(authenticated_user, encrypted_folder_path)
                        
                        secure_conn.send("OK|Upload e extração do .zip concluídos!".encode('utf-8'))
                        print(f"[UPLOAD_ZIP] Pasta '{logical_folder_name}' criada e .zip extraído para {authenticated_user}.")
                        
                    except Exception as e:
                        secure_conn.send(f"ERRO|Falha ao processar .zip: {e}".encode('utf-8'))

                else:
                    secure_conn.send("ERRO|Comando desconhecido.".encode('utf-8'))

            else:
                secure_conn.send("ERRO|Ação não permitida. Faça a autenticação primeiro.".encode('utf-8'))

    except (ssl.SSLEOFError, ConnectionResetError):
        print(f"[CONEXÃO INTERROMPIDA] {addr} desconectou abruptamente.")

    except Exception as e:
        print(f"[ERRO] Erro na conexão com {addr}: {e}")

    finally:
        print(f"[CONEXÃO FECHADA] {addr}")
        secure_conn.close()


def main():
    setup_storage()

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[ESCUTANDO] Servidor seguro está escutando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        secure_conn = context.wrap_socket(conn, server_side=True)
        thread = threading.Thread(target=handle_client, args=(secure_conn, addr))
        thread.start()


if __name__ == "__main__":
    main()