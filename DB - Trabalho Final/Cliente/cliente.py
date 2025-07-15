import socket
import threading
import sys
import tkinter as tk
import os
import ssl
import json
import time
import base64
import zipfile
import io
import traceback
from tkinter import filedialog, messagebox, Entry, Label, Button, ttk, simpledialog
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from datetime import datetime


HOST = 'localhost'
PORT = 0
BUFFER_SIZE = 4096


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def format_bytes(size):
    if size == 0: return "0 B"
    power, n = 1024, 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power and n < len(power_labels):
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


def encrypt_filename(key: bytes, filename: str) -> str:
    iv = os.urandom(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()
    
    encrypted_bytes = encryptor.update(filename.encode('utf-8')) + encryptor.finalize()
    tag = encryptor.tag
    
    safe_name_bytes = base64.urlsafe_b64encode(iv + tag + encrypted_bytes)
    return safe_name_bytes.decode('utf-8')


def decrypt_filename(key: bytes, encrypted_name: str) -> str:
    try:
        encrypted_bytes_with_meta = base64.urlsafe_b64decode(encrypted_name.encode('utf-8'))
        
        iv = encrypted_bytes_with_meta[:12]
        tag = encrypted_bytes_with_meta[12:28]
        encrypted_data = encrypted_bytes_with_meta[28:]
        
        decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
        
        decrypted_bytes = decryptor.update(encrypted_data) + decryptor.finalize()
        return decrypted_bytes.decode('utf-8')
    
    except Exception:
        return encrypted_name


def encrypt_file(key: bytes, in_path: str, out_path: str):
    iv = os.urandom(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()
    
    with open(in_path, 'rb') as f_in, open(out_path, 'wb') as f_out:
        f_out.write(iv)
        
        while True:
            chunk = f_in.read(BUFFER_SIZE)
            if not chunk:
                break
            encrypted_chunk = encryptor.update(chunk)
            f_out.write(encrypted_chunk)
            
        f_out.write(encryptor.finalize() + encryptor.tag)


def decrypt_file(key: bytes, in_path: str, out_path: str):
    with open(in_path, 'rb') as f_in:
        iv = f_in.read(12) 
        tag = f_in.seek(-16, os.SEEK_END)
        tag = f_in.read(16)
        
        f_in.seek(12)
        encrypted_data = f_in.read(os.path.getsize(in_path) - 12 - 16)
        
    decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    with open(out_path, 'wb') as f_out:
        f_out.write(decrypted_data)


def encrypt_data(key: bytes, data: bytes) -> bytes:
    iv = os.urandom(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend()).encryptor()
    
    encrypted_data = encryptor.update(data) + encryptor.finalize()
    
    return iv + encrypted_data + encryptor.tag


def decrypt_data(key: bytes, encrypted_data: bytes) -> bytes:
    try:
        iv = encrypted_data[:12]
        tag = encrypted_data[-16:]
        data_to_decrypt = encrypted_data[12:-16]
        
        decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()).decryptor()
        
        return decryptor.update(data_to_decrypt) + decryptor.finalize()
    except Exception as e:
        print(f"Falha na descriptografia dos dados: {e}")
        return encrypted_data 


class CloudClient:
    def __init__(self, root):
        self.root = root
        self.root.title("SB - SaveBox")
        self.user_salt = None
        self.encryption_key = None
        self.sock = None
        self.current_frame = None
        self.file_data = []
        self.action_buttons = []
        self.current_path = ""
        self.decrypted_path = ""

        try:
            icon_path = resource_path('icons/icon.ico') 
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Aviso: Não foi possível carregar o ícone da janela: {e}")

        try:
            icon_path = 'icons/' 
            self.folder_icon = tk.PhotoImage(file=resource_path('icons/folder.png'))
            self.text_icon = tk.PhotoImage(file=resource_path('icons/text.png'))
            self.pdf_icon = tk.PhotoImage(file=resource_path('icons/pdf.png'))
            self.enc_icon = tk.PhotoImage(file=resource_path('icons/enc.png'))
            self.image_icon = tk.PhotoImage(file=resource_path('icons/image.png'))
            self.video_icon = tk.PhotoImage(file=resource_path('icons/video.png'))
            self.audio_icon = tk.PhotoImage(file=resource_path('icons/audio.png'))
            self.zip_icon = tk.PhotoImage(file=resource_path('icons/zip.png'))
            self.code_icon = tk.PhotoImage(file=resource_path('icons/code.png'))
            self.file_icon = tk.PhotoImage(file=resource_path('icons/file.png'))
            self.pem_icon = tk.PhotoImage(file=resource_path('icons/pem.png'))
        except tk.TclError:
            Exception("Erro ao carregar os ícones.")

        self.switch_to_login_view()


    def _schedule_gui_update(self, func, *args):
        self.root.after(0, func, *args)


    def setup_context_menus(self):
        # Menu para quando clicar em um ARQUIVO
        self.file_context_menu = tk.Menu(self.root, tearoff=0)
        self.file_context_menu.add_command(label="Baixar Arquivo", command=self.download_file)
        self.file_context_menu.add_command(label="Deletar", command=self.delete_item)

        # Menu para quando clicar em uma PASTA
        self.folder_context_menu = tk.Menu(self.root, tearoff=0)
        self.folder_context_menu.add_command(label="Baixar como .zip", command=self.download_folder_as_zip)
        self.folder_context_menu.add_command(label="Deletar", command=self.delete_item)
        
        # Menu para quando clicar em uma ÁREA VAZIA
        self.empty_context_menu = tk.Menu(self.root, tearoff=0)
        self.empty_context_menu.add_command(label="Novo Arquivo", command=self.upload_file)
        self.empty_context_menu.add_command(label="Nova Pasta", command=self.create_new_folder)
        self.empty_context_menu.add_command(label="Criar pasta de um .zip", command=self.upload_zip_as_folder)
        self.empty_context_menu.add_command(label="Baixar pasta atual como .zip", command=self.download_folder_as_zip)
        self.empty_context_menu.add_separator() 
        self.empty_context_menu.add_command(label="Atualizar", command=self.refresh_files)


    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        
        if item_id:
            self.tree.selection_set(item_id)
            item_details = self.tree.item(item_id)
            item_type = item_details['tags'][0]
            
            if item_type == 'folder':
                self.folder_context_menu.post(event.x_root, event.y_root)
            else:
                self.file_context_menu.post(event.x_root, event.y_root)
        else:
            self.empty_context_menu.post(event.x_root, event.y_root)


    def _update_progress_display(self, current_bytes, total_bytes, start_time, prefix=""):
        if total_bytes == 0:
            percentage = 0
        else:
            percentage = (current_bytes / total_bytes) * 100

        self.progress_bar['value'] = percentage
        elapsed_time = time.time() - start_time
        speed = 0
        if elapsed_time > 0:
            speed = current_bytes / elapsed_time

        status_text = (f"{prefix}: {format_bytes(current_bytes)} / {format_bytes(total_bytes)} ({percentage:.1f}%) - {format_bytes(speed)}/s")
        self.progress_label.config(text=status_text)


    def _sort_and_display(self, sort_key, reverse_order):
        if sort_key == 'name':
            self.file_data.sort(key=lambda item: item['name'].lower(), reverse=reverse_order)
        else:
            self.file_data.sort(key=lambda item: item[sort_key], reverse=reverse_order)

        self._populate_treeview()


    def _on_sort_select(self, event=None):
        selected_option_text = self.sort_combobox.get()
        sort_key, reverse_order = self.sort_options[selected_option_text]
        self._sort_and_display(sort_key, reverse_order)


    def _populate_treeview(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        if self.current_path:
            self.tree.insert('', 0, text=" ..", 
                             image=self.folder_icon, 
                             values=("", ""), 
                             tags=('folder', '..'))

        if not self.encryption_key:
            self.update_status("Erro: Chave de criptografia não disponível.")
            return

        for item in self.file_data:
            encrypted_filename = item['name']
            display_name = decrypt_filename(self.encryption_key, encrypted_filename)
            item_type = item['type']

            if item_type == 'folder':
                icon_to_use = self.folder_icon
            else:
                if display_name.endswith('.txt'):
                    icon_to_use = self.text_icon
                elif display_name.endswith('.pdf'):
                    icon_to_use = self.pdf_icon
                elif display_name.endswith('.enc'):
                    icon_to_use = self.enc_icon
                elif display_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    icon_to_use = self.image_icon
                elif display_name.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                    icon_to_use = self.video_icon
                elif display_name.lower().endswith(('.mp3', '.wav', '.flac')):
                    icon_to_use = self.audio_icon
                elif display_name.lower().endswith(('.zip', '.rar', '.tar', '.gz')):
                    icon_to_use = self.zip_icon
                elif display_name.lower().endswith(('.py', '.js', '.html', '.css', 'json', '.xml', '.java', '.c', '.cpp')):
                    icon_to_use = self.code_icon
                elif display_name.lower().endswith(('.enc')):
                    icon_to_use = self.enc_icon
                elif display_name.lower().endswith('.pem'):
                    icon_to_use = self.pem_icon
                else:
                    icon_to_use = self.file_icon
            
            file_size = format_bytes(item['size']) if item_type == 'file' else ""
            file_date_str = datetime.fromtimestamp(item['date']).strftime('%d/%m/%Y %H:%M:%S')
            
            tag_to_use = item_type if item_type == 'folder' else ''
            
            self.tree.insert('', tk.END, 
                             text=f" {display_name}", 
                             image=icon_to_use, 
                             values=(file_size, file_date_str), 
                             tags=(tag_to_use, encrypted_filename))


    def _go_up_directory(self):
        if self.current_path:
            self.current_path = os.path.dirname(self.current_path).replace("\\", "/")
            self.decrypted_path = os.path.dirname(self.decrypted_path)
            self.refresh_files()


    def _on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        item_details = self.tree.item(item_id)
        
        item_type = item_details['tags'][0]
        item_name_encrypted = item_details['tags'][1]
        
        if item_type == 'folder':
            if item_name_encrypted == '..':
                self._go_up_directory()

            else:
                self.current_path = os.path.join(self.current_path, item_name_encrypted).replace("\\", "/")
                self.decrypted_path = os.path.join(self.decrypted_path, decrypt_filename(self.encryption_key, item_name_encrypted)).replace("\\", "/")
                self.refresh_files()


    def create_new_folder(self):
        folder_name = simpledialog.askstring("Nova Pasta", "Digite o nome da nova pasta:", parent=self.root)
        if folder_name:
            key = self.encryption_key
            
            encrypted_folder_name = encrypt_filename(key, folder_name)
            
            new_folder_path = os.path.join(self.current_path, encrypted_folder_name).replace("\\", "/")
            
            self.run_in_thread(self._create_folder_task, new_folder_path)


    def _create_folder_task(self, folder_path):
        try:
            self.update_status(f"Criando pasta '{os.path.basename(folder_path)}'...")
            self.sock.send(f"CREATE_FOLDER|{folder_path}".encode('utf-8'))
            response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
            if response[0] == "OK":
                self.update_status("Pasta criada com sucesso.")
                self.refresh_files()
            else:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta: {response[1]}")
        except Exception as e:
            messagebox.showerror("Erro de Rede", f"Falha ao se comunicar com o servidor: {e}")


    def run_in_thread(self, target_func, *args, **kwargs):
        thread = threading.Thread(target=target_func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()


    def _download_task(self, server_path, save_path, is_folder=False):
        self._schedule_gui_update(self._disable_actions)
        filesize, bytes_received = 0, 0
        try:
            command_to_send = "DOWNLOAD_FOLDER_AS_ZIP" if is_folder else "DOWNLOAD"
            self.sock.send(f"{command_to_send}|{server_path}".encode('utf-8'))
            
            header = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
            if header[0] != "OK":
                self.update_status(f"Erro do servidor: {header[1]}"); return

            filesize = int(header[1])
            self.sock.send("OK".encode('utf-8'))
            
            start_time = time.time()
            self._schedule_gui_update(self._update_progress_display, 0, filesize, start_time, "Baixando")

            in_memory_download = io.BytesIO()
            while bytes_received < filesize:
                chunk = self.sock.recv(min(filesize - bytes_received, BUFFER_SIZE))
                if not chunk: break
                in_memory_download.write(chunk)
                bytes_received += len(chunk)
                self._schedule_gui_update(self._update_progress_display, bytes_received, filesize, start_time, "Baixando")

            if bytes_received < filesize: self.update_status("Download falhou."); return

            if is_folder:
                self.update_status("Processando e descriptografando o .zip...")
                in_memory_download.seek(0)
                in_memory_final_zip = io.BytesIO()

                with zipfile.ZipFile(in_memory_download, 'r') as encrypted_zip, \
                     zipfile.ZipFile(in_memory_final_zip, 'w', zipfile.ZIP_DEFLATED) as decrypted_zip:
                    
                    for item_info in encrypted_zip.infolist():
                        encrypted_path = item_info.filename
                        path_parts = encrypted_path.replace('\\', '/').rstrip('/').split('/')
                        decrypted_parts = [decrypt_filename(self.encryption_key, part) for part in path_parts]
                        decrypted_path = "/".join(decrypted_parts)

                        if item_info.is_dir():
                            decrypted_zip.writestr(decrypted_path + '/', b'')
                        else:
                            encrypted_content = encrypted_zip.read(item_info.filename)
                            decrypted_content = decrypt_data(self.encryption_key, encrypted_content)
                            decrypted_zip.writestr(decrypted_path, decrypted_content)
                
                self.update_status("Salvando arquivo .zip final...")
                with open(save_path, 'wb') as f_out:
                    f_out.write(in_memory_final_zip.getvalue())
                self.update_status(f"Arquivo '{os.path.basename(save_path)}' salvo com sucesso!")
            else:
                self.update_status("Descriptografando arquivo...")
                encrypted_content = in_memory_download.getvalue()
                decrypted_content = decrypt_data(self.encryption_key, encrypted_content)
                with open(save_path, 'wb') as f_out: f_out.write(decrypted_content)
                self.update_status(f"Download de '{os.path.basename(save_path)}' concluído!")

        except Exception as e:
            self.update_status(f"Erro no processamento do download: {e}"); traceback.print_exc()
        finally:
            self._schedule_gui_update(self._enable_actions)
            self.root.after(2000, lambda: self.progress_bar.config(value=0))


    def download_file(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return messagebox.showwarning("Atenção", "Selecione um item para baixar.")
        
        item_id = selected_items[0]
        item_details = self.tree.item(item_id)
        
        item_type = item_details['tags'][0]
        if item_type == 'folder':
            self.download_folder_as_zip()
            return

        decrypted_filename = item_details['text'].strip() 
        encrypted_filename = item_details['tags'][1]
        

        _name, extension = os.path.splitext(decrypted_filename)

        file_types = [
            (f"Arquivo {extension.upper()}", f"*{extension}"),
            ("Todos os arquivos", "*.*")
        ]
        
        save_path = filedialog.asksaveasfilename(
            initialfile=decrypted_filename,
            defaultextension=extension, 
            filetypes=file_types      
        )

        item_path_on_server = os.path.join(self.current_path, encrypted_filename).replace("\\", "/")

        
        if save_path:
            self.run_in_thread(self._download_task, item_path_on_server, save_path, is_folder=False)


    def _upload_task(self, local_path, remote_path):
        self._schedule_gui_update(self._disable_actions)
        temp_encrypted_path = local_path + ".enc"
        try:
            self.update_status("Criptografando arquivo localmente...")
            key = self.encryption_key
            encrypt_file(key, local_path, temp_encrypted_path)
            
            filesize = os.path.getsize(temp_encrypted_path)
            start_time = time.time()
            self._schedule_gui_update(self._update_progress_display, 0, filesize, start_time, "Iniciando Upload")
            
            self.sock.send(f"UPLOAD|{remote_path}|{filesize}".encode('utf-8'))
            if self.sock.recv(BUFFER_SIZE).decode('utf-8') != "OK":
                self.update_status("Upload recusado pelo servidor.")
                return

            bytes_sent = 0
            with open(temp_encrypted_path, 'rb') as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk: break
                    self.sock.sendall(chunk)
                    bytes_sent += len(chunk)
                    self._schedule_gui_update(self._update_progress_display, bytes_sent, filesize, start_time, "Enviando")

            final_response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
            if final_response[0] != "OK":
                raise Exception(f"Erro no servidor após upload: {final_response[1] if len(final_response) > 1 else 'Resposta inválida'}")

            self.update_status(f"Upload de '{os.path.basename(local_path)}' concluído!")
            self.refresh_files()

        except Exception as e:
            self.update_status(f"Erro no upload: {e}")
            traceback.print_exc()

        finally:
            if os.path.exists(temp_encrypted_path):
                os.remove(temp_encrypted_path)
            self._schedule_gui_update(self._enable_actions)
            self.root.after(2000, lambda: self.progress_bar.config(value=0))


    def upload_file(self):
        local_filepath = filedialog.askopenfilename()
        if not local_filepath:
            return

        key = self.encryption_key
        original_filename = os.path.basename(local_filepath)
        
        encrypted_filename = encrypt_filename(key, original_filename)
        
        upload_path = os.path.join(self.current_path, encrypted_filename).replace("\\", "/")
        
        self.run_in_thread(self._upload_task, local_filepath, upload_path)


    def _delete_task(self, item_path):
        try:
            self.update_status(f"Deletando '{os.path.basename(item_path)}'...")
            
            self.sock.send(f"DELETE|{item_path}".encode('utf-8'))
            
            response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
            
            if response[0] == "OK":
                self.update_status("Item deletado com sucesso.")
                self.refresh_files()
            else:
                self.update_status(f"Erro ao deletar: {response[1]}")
                messagebox.showerror("Erro", f"Não foi possível deletar o item: {response[1]}")

        except Exception as e:
            self.update_status(f"Falha na comunicação: {e}")
            messagebox.showerror("Erro de Rede", f"Falha ao se comunicar com o servidor: {e}")


    def delete_item(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return messagebox.showwarning("Atenção", "Selecione um arquivo ou pasta para deletar.")
        
        item_id = selected_items[0]
        item_details = self.tree.item(item_id)
        
        item_name_decrypted = item_details['text']
        item_name_encrypted = item_details['tags'][1]

        item_path_on_server = os.path.join(self.current_path, item_name_encrypted).replace("\\", "/")
        
        if messagebox.askyesno("Confirmar Deleção", f"Você tem certeza que deseja apagar permanentemente '{item_name_decrypted}'?"):
            self.run_in_thread(self._delete_task, item_path_on_server)


    def download_folder_as_zip(self):
        selected_items = self.tree.selection()
        if not selected_items:
            # Se nenhum item está selecionado, baixar a pasta atual
            folder_path_on_server = self.current_path
            current_folder_name = os.path.basename(self.decrypted_path) if self.decrypted_path else "root"
            
            save_path = filedialog.asksaveasfilename(
                initialfile=f"{current_folder_name}.zip",
                defaultextension=".zip",
                filetypes=[("Arquivo Zip", "*.zip")]
            )
            
            if save_path:
                self.run_in_thread(self._download_task, folder_path_on_server, save_path, is_folder=True)
            return
        
        item_details = self.tree.item(selected_items[0])
        folder_name_decrypted = item_details['text']
        folder_name_encrypted = item_details['tags'][1]

        folder_path_on_server = os.path.join(self.current_path, folder_name_encrypted).replace("\\", "/")

        save_path = filedialog.asksaveasfilename(
            initialfile=f"{folder_name_decrypted}.zip",
            defaultextension=".zip",
            filetypes=[("Arquivo Zip", "*.zip")]
        )
        
        if save_path:
            self.run_in_thread(self._download_task, folder_path_on_server, save_path, is_folder=True)


    def upload_zip_as_folder(self):
        zip_filepath = filedialog.askopenfilename(
            title="Selecione um arquivo .zip para criar uma pasta",
            filetypes=[("Arquivos Zip", "*.zip")]
        )
        if not zip_filepath:
            return

        folder_name = os.path.basename(zip_filepath).removesuffix('.zip')
        
        self.run_in_thread(self._upload_zip_task, zip_filepath, folder_name)


    def _upload_zip_task(self, zip_filepath, root_folder_name):
        self._schedule_gui_update(self._disable_actions)
        key = self.encryption_key
        try:
            self.update_status("Processando .zip e criptografando conteúdo...")
            
            filename_cache = {}
            
            def encrypt_filename_cached(filename):
                if filename not in filename_cache:
                    filename_cache[filename] = encrypt_filename(key, filename)
                return filename_cache[filename]
            
            memory_zip = io.BytesIO()
            with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as encrypted_zip:
                with zipfile.ZipFile(zip_filepath, 'r') as original_zip:
                    
                    for item_info in original_zip.infolist():
                        path_in_zip = item_info.filename
                        if path_in_zip.startswith('__MACOSX/') or not path_in_zip.strip():
                            continue
                        
                        if item_info.is_dir():
                            path_parts = path_in_zip.replace('\\', '/').rstrip('/').split('/')
                            
                            encrypted_parts = []
                            for part in path_parts:
                                if part: 
                                    encrypted_part = encrypt_filename_cached(part)
                                    encrypted_parts.append(encrypted_part)
                            
                            encrypted_path = '/'.join(encrypted_parts) + '/'
                            encrypted_zip.writestr(encrypted_path, b'')
                        else:
                            path_parts = path_in_zip.replace('\\', '/').split('/')
                            
                            encrypted_parts = []
                            for part in path_parts:
                                if part:
                                    encrypted_part = encrypt_filename_cached(part)
                                    encrypted_parts.append(encrypted_part)
                            
                            encrypted_path = '/'.join(encrypted_parts)
                            
                            file_content = original_zip.read(item_info.filename)
                            encrypted_content = encrypt_data(key, file_content)
                            encrypted_zip.writestr(encrypted_path, encrypted_content)
            
            memory_zip.seek(0)
            zip_data = memory_zip.getvalue()
            filesize = len(zip_data)
            
            self.update_status("Enviando .zip processado para o servidor...")
            
            encrypted_root_folder_name = encrypt_filename_cached(root_folder_name)
            remote_zip_path = os.path.join(self.current_path, encrypted_root_folder_name).replace("\\", "/")
            
            command = f"UPLOAD_ZIP_AS_FOLDER|{remote_zip_path}|{filesize}"
            self.sock.send(command.encode('utf-8'))
            response = self.sock.recv(BUFFER_SIZE).decode('utf-8')
            if response != "OK":
                self.update_status("Upload recusado pelo servidor.")
                return

            start_time = time.time()
            bytes_sent = 0
            chunk_size = BUFFER_SIZE
            
            while bytes_sent < filesize:
                chunk = zip_data[bytes_sent:bytes_sent + chunk_size]
                self.sock.sendall(chunk)
                bytes_sent += len(chunk)
                self._schedule_gui_update(self._update_progress_display, bytes_sent, filesize, start_time, "Enviando")

            final_response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
            if final_response[0] != "OK":
                raise Exception(f"Erro no servidor: {final_response[1] if len(final_response) > 1 else 'Resposta inválida'}")

            self.update_status("Upload do .zip concluído!")
            self.refresh_files()
        except Exception as e:
            self.update_status(f"Erro durante o upload do .zip: {e}")
            traceback.print_exc()
        finally:
            self._schedule_gui_update(self._enable_actions)
            self.root.after(2000, lambda: self.progress_bar.config(value=0))


    def _refresh_files_task(self):
        try:
            self._schedule_gui_update(self.path_label.config, {'text': f"Caminho: /{self.decrypted_path.replace('/', ' / ')}"})
            
            self.update_status("Atualizando lista de arquivos...")
            

            self.sock.send(f"LIST|{self.current_path}".encode('utf-8'))
            

            header_bytes = self.sock.recv(10)
            if not header_bytes:
                raise ConnectionError("A conexão com o servidor foi perdida.")
            
            message_length = int(header_bytes.decode('utf-8').strip())

            full_response_bytes = b''
            bytes_received = 0
            while bytes_received < message_length:
                remaining = message_length - bytes_received
                chunk = self.sock.recv(min(remaining, BUFFER_SIZE))
                if not chunk:
                    raise ConnectionError("A conexão foi perdida durante o recebimento da lista.")
                full_response_bytes += chunk
                bytes_received += len(chunk)
            
            self.file_data = json.loads(full_response_bytes.decode('utf-8'))

            self._on_sort_select() 
            self.update_status("Lista de arquivos atualizada.")
            
        except Exception as e:
            self.update_status(f"Erro ao obter lista de arquivos: {e}")


    def refresh_files(self):
        self.run_in_thread(self._refresh_files_task)


    def _get_stats_task(self):
        try:
            self.update_status("Buscando estatísticas...")
            self.sock.send("GET_STATS".encode('utf-8'))
            response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')

            if response[0] == "STATS":
                up_count, down_count, up_bytes, down_bytes = response[1], response[2], format_bytes(int(response[3])), format_bytes(int(response[4]))
                stats_message = (f"Estatísticas de Uso - {self.username}\n\n"
                                 f"Uploads:\n  - Arquivos enviados: {up_count}\n  - Total de dados: {up_bytes}\n\n"
                                 f"Downloads:\n  - Arquivos baixados: {down_count}\n  - Total de dados: {down_bytes}")
                messagebox.showinfo("Minhas Estatísticas", stats_message)
                self.update_status("Estatísticas exibidas.")
            else:
                messagebox.showerror("Erro", response[1])

        except Exception as e:
            self.update_status(f"Falha na comunicação: {e}")


    def show_my_stats(self):
        self.run_in_thread(self._get_stats_task)


    def update_status(self, message):
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text=message)
            self.root.update_idletasks()


    def connect_to_server(self):
        host = self.host_entry.get()
        port_str = self.port_entry.get()

        if not host or not port_str:
            messagebox.showerror("Erro de Conexão", "Host e Porta do servidor são obrigatórios.")
            return False

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Erro de Conexão", "A porta deve ser um número válido.")
            return False

        try:
            cert_path = resource_path("cert.pem")
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cert_path)
            context.check_hostname = False
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.sock = context.wrap_socket(sock, server_hostname=host)
            self.sock.connect((host, port))
            return True
        
        except FileNotFoundError:
            messagebox.showerror("Erro de Configuração", "Arquivo 'cert.pem' não encontrado.")
            return False
        
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar a {host}:{port}\n\nErro: {e}")
            return False
        

    def login(self):
        self.username = self.login_entry.get()
        password = self.password_entry.get()

        if not self.username or not password:
            return messagebox.showerror("Erro", "Login e senha são obrigatórios.")
        
        if not self.connect_to_server():
            return
        
        self.sock.send(f"AUTH|{self.username}|{password}".encode('utf-8'))
        response = self.sock.recv(BUFFER_SIZE).decode('utf-8').split('|')
        
        if response[0] == "OK":
            salt_hex = response[1]
            self.user_salt = bytes.fromhex(salt_hex)
            self.encryption_key = derive_key(password, self.user_salt)
            self.switch_to_main_view()
        else:
            messagebox.showerror("Falha na Autenticação", response[1])
            self.sock.close()


    def logout(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.update_status(f"Erro ao desconectar: {e}")
        
        self.sock = None
        self.username = ""
        self.file_data = []

        self.switch_to_login_view()


    def register(self):
        login = self.login_entry.get()
        password = self.password_entry.get()
        host = self.host_entry.get()
        port_str = self.port_entry.get()
        port = int(port_str)

        if not login or not password:
            messagebox.showerror("Erro", "Login e senha são obrigatórios.")
            return
        
        temp_sock = None

        try:
            cert_path = resource_path("cert.pem")
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cert_path)
            context.check_hostname = False
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_sock = context.wrap_socket(sock, server_hostname=HOST)
            temp_sock.connect((host, port))
            temp_sock.send(f"REGISTER|{login}|{password}".encode('utf-8'))
            response = temp_sock.recv(BUFFER_SIZE).decode('utf-8').split('|')

            if response[0] == "OK":
                messagebox.showinfo("Sucesso", f"{response[1]}\nAgora você pode fazer o login.")
            else:
                messagebox.showerror("Erro no Registro", response[1])

        except Exception as e:
            messagebox.showerror("Erro no Registro", f"Não foi possível conectar: {e}")

        finally:
            if temp_sock:
                temp_sock.close()


    def switch_to_login_view(self):
        if self.current_frame:
            self.current_frame.destroy()

        self.root.geometry("400x280")
        
        self.current_frame = tk.Frame(self.root)
        self.current_frame.pack(fill="both", expand=True)

        login_container = tk.Frame(self.current_frame)
        login_container.pack(expand=True)


        Label(login_container, text="Host:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_entry = Entry(login_container, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)

        self.host_entry.insert(0, "localhost")

        Label(login_container, text="Porta:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.port_entry = Entry(login_container, width=30)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        self.port_entry.insert(0, "65432")
        
        Label(login_container, text="Login:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.login_entry = Entry(login_container, width=30)
        self.login_entry.grid(row=2, column=1, padx=5, pady=5)

        Label(login_container, text="Senha:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = Entry(login_container, show="*", width=30)
        self.password_entry.grid(row=3, column=1, padx=5, pady=5)

        button_frame = tk.Frame(login_container)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        Button(button_frame, text="Login", command=self.login).pack(side=tk.LEFT, padx=5)
        Button(button_frame, text="Registrar", command=self.register).pack(side=tk.LEFT, padx=5)


    def switch_to_main_view(self):
        if self.current_frame:
            self.current_frame.destroy()

        self.setup_context_menus()
        
        self.root.geometry("800x500") 
        self.current_frame = tk.Frame(self.root)
        self.current_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        top_frame = tk.Frame(self.current_frame)
        top_frame.pack(fill="both", expand=True)
        
        progress_frame = tk.Frame(self.current_frame)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10,0))

        left_panel = tk.Frame(top_frame, width=180, bg="#f0f0f0")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False) 

        right_panel = tk.Frame(top_frame)
        right_panel.pack(side=tk.RIGHT, fill="both", expand=True)


        sort_frame = tk.Frame(left_panel, bg="#f0f0f0")
        sort_frame.pack(pady=10, padx=10, fill='x') 
        Label(sort_frame, text="Ordenar por:", bg="#f0f0f0").pack(anchor='w')
        self.sort_options = {
            "Nome (A-Z)": ('name', False), "Nome (Z-A)": ('name', True),
            "Tamanho ↓": ('size', True), "Tamanho ↑": ('size', False),
            "Data (Mais Recente)": ('date', True), "Data (Mais Antiga)": ('date', False),
        }
        self.sort_combobox = ttk.Combobox(sort_frame, values=list(self.sort_options.keys()), state="readonly")
        self.sort_combobox.pack(fill='x', pady=(5,0))
        self.sort_combobox.set("Nome (A-Z)") 
        self.sort_combobox.bind("<<ComboboxSelected>>", self._on_sort_select)

        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10, padx=5)

        self.upload_button = Button(left_panel, text="Fazer Upload", command=self.upload_file)
        self.upload_button.pack(fill='x', padx=10, pady=5)
        
        self.download_button = Button(left_panel, text="Fazer Download", command=self.download_file)
        self.download_button.pack(fill='x', padx=10, pady=5)
        
        self.refresh_button = Button(left_panel, text="Atualizar Lista", command=self.refresh_files)
        self.refresh_button.pack(fill='x', padx=10, pady=5)

        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=10, padx=5)
        
        self.stats_button = Button(left_panel, text="Minhas Estatísticas", command=self.show_my_stats)
        self.stats_button.pack(fill='x', padx=10, pady=5)
        

        self.logout_button = Button(left_panel, text="Logout", command=self.logout)
        self.logout_button.pack(side=tk.BOTTOM, fill='x', padx=10, pady=10)
        

        self.action_buttons = [
            self.upload_button, self.download_button, 
            self.refresh_button, self.stats_button, self.logout_button
        ]
        
        # Parte Principal da Tela

        self.path_label = Label(right_panel, text=f"Caminho: /", anchor='w', fg="grey")
        self.path_label.pack(fill='x', padx=5)
        
        tree_frame = tk.Frame(right_panel)
        tree_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=('Tamanho', 'Data de Modificação'), show='tree headings')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<Double-1>", self._on_item_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
        
        self.tree.heading('#0', text='Nome do Arquivo'); self.tree.heading('Tamanho', text='Tamanho'); self.tree.heading('Data de Modificação', text='Data de Modificação')
        self.tree.column('#0', anchor='w', width=250, stretch=tk.YES); self.tree.column('Tamanho', anchor='e', width=100); self.tree.column('Data de Modificação', anchor='center', width=160)
        
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Progress Bar
        
        self.progress_label = Label(progress_frame, text="Pronto.")
        self.progress_label.pack(fill=tk.X)
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, expand=True)
        
        # Inicializa a tela
        self.update_status(f"Logado como {self.username}. Bem-vindo!")
        self.refresh_files()


    def _disable_actions(self):
        for button in self.action_buttons:
            button.config(state=tk.DISABLED)

        for menu in [self.file_context_menu, self.folder_context_menu, self.empty_context_menu]:
            last_index = menu.index('end')
            if last_index is not None:
                for i in range(last_index + 1):
                    if menu.type(i) == 'command':
                        menu.entryconfig(i, state=tk.DISABLED)


    def _enable_actions(self):
        for button in self.action_buttons:
            button.config(state=tk.NORMAL)

        for menu in [self.file_context_menu, self.folder_context_menu, self.empty_context_menu]:
            last_index = menu.index('end')
            if last_index is not None:
                for i in range(last_index + 1):
                    if menu.type(i) == 'command':
                        menu.entryconfig(i, state=tk.NORMAL)

    def on_closing(self):
        if self.sock:
            self.sock.close()
        self.root.destroy()



if __name__ == "__main__":
    root = tk.Tk()
    app = CloudClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()