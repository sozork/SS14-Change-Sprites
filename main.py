import compress_decompress, sqlite3
import os
import base64
import customtkinter as ctk
from PIL import Image
import io
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
def set_db_data(content_path, path, image_path):
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
def save_current_image(content_path, path):
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
def get_display_sprites(content_path, search_param):
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
            data = compress_decompress.decompress(data)
        pairs.append((i[0], instance_path, data, compression))
    
    return pairs
        
# Разные фреймы
# Стартовый фрейм
class StartPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        # кнопки для перехода в различные фреймы приложения
        self.changespr_btn = ctk.CTkButton(self, text='Change Sprites', command=lambda:(master.ChangesprPage.grid(**master.ChangesprPage.griddata), self.grid_forget())) # При нажатии Changespr  - показывает окно смены спрайтов и скрывает стартовое окно
        self.changespr_btn.grid(column = 0)
        self.backups_btn = ctk.CTkButton(self, text='Backups')
        self.backups_btn.grid(column = 1, row = 0)
        self.packs_btn = ctk.CTkButton(self, text='Packs')
        self.packs_btn.grid(column = 2, row = 0)
    
# Фрейм смены спрайтов
class ChangesprPage(ctk.CTkFrame):
    def __init__(self, master, griddata):
        super().__init__(master)
        # хэсшмап для пути до бд и пути до спрайта на который меняют
        self.dict = {"content_path":"", "change_image_to_path": ""}
        # свойства грида где он будет
        self.griddata = griddata 
        # кнопочка для выбора пути до контента
        self.contentpath_btn = ctk.CTkButton(self, text='Content, path', command = lambda:self.get_file("content_path", [('DB', '*.db')])) # лямбду нужно ставить что бы функция не вызывалась при запуске
        self.contentpath_btn.grid(column = 0)

        # кнопочка выбора пути до картинки для смены
        self.changeimgpath_btn = ctk.CTkButton(self, text='Image to change to, path', command = lambda:self.get_file("change_image_to_path", [("PNG","*.png"),("JPG","*.jpg"),("JPEG","*.jpeg")]))
        self.changeimgpath_btn.grid(column = 1, row = 0)

        # создания ввод парамтров поиска
        self.entry = ctk.CTkEntry(master=self, width=400, height=50)
        self.entry.grid(row=1, column=0, columnspan = 2)
        self.entry.bind("<Return>", self.show_sprites)

    # получаем файлы(фото для смены и путь до контента)
    def get_file(self, key, filetypes):
        self.dict[key] = ctk.filedialog.askopenfilename(filetypes=filetypes)

    # Показ спрайтов
    def show_sprites(self, e):
        # создаём фрейм чисто для спрайтов
        self.imageframe = ctk.CTkScrollableFrame(master=self, width=400)
        self.imageframe.grid(column = 0, row = 3, columnspan = 2)
        if self.dict["content_path"] == "":
            pass
        else:
            pairs = get_display_sprites(self.dict["content_path"], self.entry.get())
            print("pairs retrived, starting showing proccess")
            n = len(pairs)
            lenx = 2
            leny = n//2
            print(n, lenx, leny)
            for row in range(leny):
                for column in range(lenx):
                    if not row*leny + column < n:
                        break
                    else:
                        print('niguuuuur')
                        pair = pairs[row*leny + column]
                        print(row, column)
                        content_id, path, data, compression = pair[0], pair[1], pair[2], pair[3]
                        image = Image.open(io.BytesIO(data)) 
                        self.imageframe.img_btn = ctk.CTkButton(self.imageframe, image=ctk.CTkImage(light_image=image, dark_image=image, size=(self.contentpath_btn.cget("width"), self.contentpath_btn.cget("width"))), text = "")
                        self.imageframe.img_btn.grid(row = row+1, column = column+1)
            

            pass

# само приложение
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SS14 Change Sprites")
        self.geometry("1000x840")

        self.grid_rowconfigure(0, weight=1)      # я не понял почему, но без этого не работает align гридов
        self.grid_columnconfigure(0, weight=1)

        self.ChangesprPage = ChangesprPage(self, {"column":0, "row":0}) # иницилизируеми сразу скрываем фрейм смены спрайтов
        self.ChangesprPage.grid_forget() 

        self.startframe = StartPage(self) # иницилизируем стартовый фрейм (всегда ставить последним, т.к в нём используются другие фреймы)
        self.startframe.grid(row=0, column=0) # align в центре

# запуск 
if __name__ == "__main__":
    app = App()
    app.mainloop()