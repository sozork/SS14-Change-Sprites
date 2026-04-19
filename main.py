import compress_decompress, sqlite3
import os
import base64
import customtkinter as ctk
# sql запросы для ну что бы обойти ограничение на размер файлов(файл нельзя сменить т.к его размер не совпадает)
remove_check = '''
PRAGMA foreign_keys = false;
CREATE TABLE "Content_new" (
    "Id"	INTEGER,
    "Hash"	BLOB NOT NULL UNIQUE,
    "Size"	INTEGER NOT NULL,
    "Compression"	INTEGER NOT NULL,
    "Data"	BLOB NOT NULL,
    PRIMARY KEY("Id" AUTOINCREMENT)
);

INSERT INTO Content_new SELECT * FROM Content;

DROP TABLE Content;

ALTER TABLE Content_new RENAME TO Content;
PRAGMA foreign_keys = true;
'''
add_check = '''
PRAGMA foreign_keys = false;
CREATE TABLE "Content_new" (
    "Id"	INTEGER,
    "Hash"	BLOB NOT NULL UNIQUE,
    "Size"	INTEGER NOT NULL,
    "Compression"	INTEGER NOT NULL,
    "Data"	BLOB NOT NULL,
    PRIMARY KEY("Id" AUTOINCREMENT),
    CONSTRAINT "UncompressedSameSize" CHECK("Compression" != 0 OR length("Data") = "Size")
);

INSERT INTO Content_new SELECT * FROM Content;

DROP TABLE Content;

ALTER TABLE Content_new RENAME TO Content;
PRAGMA foreign_keys = true;'''


# cursor.executescript((remove_check))
# СЮДА НУЖНО ПРОВЕРКУ НА БАЗУ ДАННЫХ ИЗВНЕ
not_allowed_path = ['lurker', 'scout']
dont_show_path = []
# --------------------------

content_path = ''   # то где находится твоя база данных, не путать с путём до самого спрайта

# Вставить с заменой файлы в баззу данных , берёт ид, путь до спрайта на который меняет
def set_db_data(path, image_path):
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor() #  UPDATE Content SET Data = data_var WHERE Id = content_id
    content_id = cursor.execute('SELECT ContentId FROM ContentManifest WHERE path LIKE ?', [path])
    content_id = content_id.fetchone()[0]
    compression = cursor.execute(("SELECT compression FROM Content WHERE id = "+str(content_id)))
    compression = compression.fetchone()[0]
    imagpath = cursor.execute("SELECT path FROM ContentManifest WHERE ContentId = "+str(content_id)).fetchone()[0]
    imagpath = imagpath.lower()
    with open(image_path, 'rb') as f:
        f = f.read()
    if compression != 0:
        f = compress_decompress.compress(f, compression)  
    size = len(f)
    cursor.execute("UPDATE Content SET Data = ? WHERE Id = "+str(content_id), [f])
    cursor.execute("UPDATE Content SET Size = '"+ str(size) +"' WHERE Id = "+str(content_id))
    connection.commit()
    connection.close()
# сохрание по пути до спрайта
def save_current_image(path):
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor()

    content_id = cursor.execute('SELECT ContentId FROM ContentManifest WHERE path LIKE ?', [path])
    content_id = content_id.fetchone()[0]
    compression = cursor.execute(("SELECT compression FROM Content WHERE id = "+str(content_id)))
    compression = compression.fetchone()[0]

    data = cursor.execute("SELECT data FROM Content WHERE id="+str(content_id))
    data = data.fetchone()[0]

    if compression != 0:
        data = compress_decompress.decompress(data)

    with open(os.getcwd()+"/downloaded images/"+str(len(os.listdir(os.getcwd()+"/downloaded images/")))+".png", 'wb') as f:
        f.write(data)

# Выдаёт список из bool(ид внутри бд, пути, данные из бд и степени сжатия)
def get_display_sprites(e):
    global path, content_id
    search_param = ''
    # empty_folder("/temp")
    path = "%"+search_param+"%"
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor()
    pairs = []
    content_id = cursor.execute('SELECT ContentId FROM ContentManifest WHERE path LIKE "'+str(path)+'" AND path LIKE "%.png"') # Textures/_RMC14/Mobs/Xenonids/Lurker/lurker.rsi/%
    content_id = content_id.fetchall()
    content_id = list(set(content_id))
    for i in content_id:
        compression = cursor.execute("SELECT compression FROM Content WHERE id="+str(i[0]))
        compression = compression.fetchone()[0]

        data = cursor.execute("SELECT data FROM Content WHERE id="+str(i[0]))
        data = data.fetchone()[0]
        
        instance_path = cursor.execute("SELECT path FROM ContentManifest WHERE ContentId="+str(i[0]))
        instance_path = instance_path.fetchall()[-1][0]

        if compression != 0:
            data = compress_decompress.decompress(x)
        pairs.append((i[0], instance_path, data, compression))
    
    return pairs
        
# Разные фреймы
# Стартовый фрейм
class StartPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.changespr_btn = ctk.CTkButton(self, text='Change Sprites')
        self.changespr_btn.grid(column = 0)
        self.changespr_btn2 = ctk.CTkButton(self, text='Change Sprites')
        self.changespr_btn2.grid(column = 1)
# само приложение
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SS14 Change Sprites")
        self.geometry("1000x840")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.startframe = StartPage(self)
        self.startframe.grid(row=0, column=0)
        
# запуск 
if __name__ == "__main__":
    app = App()
    app.mainloop()