import compress_decompress, sqlite3
from CTkMessagebox import CTkMessagebox
import customtkinter as ctk
from PIL import Image
import requests
import io
import pyperclip
# проверка новизны базы запретов
# types
#c - if blocked path or blocked data inside of path or data
#i - if blocked path == path or blocked data == data
not_allowed_path = [] # (path, type)
not_allowed_data = [] # (data, type)
only_allowed_path = [] # Если не пустой, то будет можно менять только те файлы, которые разрешенны
git_path = "https://github.com/sozork/banned-sprites-database/raw/refs/heads/main/database.db"
ctk.set_appearance_mode('dark')
try:
    response = requests.get(git_path)
except:
    quit()
if response.status_code == 200:
    db_bytes = response.content
    connection = sqlite3.connect(":memory:")
    connection.deserialize(db_bytes)
    cursor = connection.cursor()
    data = cursor.execute("SELECT * FROM 'banned sprites'").fetchall()
    # проход по каждой строке в бд и запись данных в списки
    for row in data:
        bandata = row[0]
        banpath = row[1]
        datatype = row[2] # не тоже самое что .png .db и тд. Это то как данные использовать
        if bandata != None:
            not_allowed_data.append((bandata, datatype))
        if banpath != None:
            not_allowed_path.append((banpath, datatype))
    # заполняем список only_allowed_path
    for path in not_allowed_path:
        if path[1] == 'a':
            only_allowed_path.append(path[0])
    connection.close()
else:   
    quit()
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
# --------------------------

content_path = ''   # то где находится твоя база данных, не путать с путём до самого спрайта
# проверка на запреты
def check_is_valid(path, data):
    # проверка на разрешённые части
    if len(only_allowed_path) > 0:
        for banpath in only_allowed_path:
            if banpath in path:
                return True
        return False
    for bandata in not_allowed_data:
        if bandata[1] == 'c':
            if bandata[0] in data:
                return False
        elif bandata[1] == 'i':
            if bandata[0] == data:
                return False
    for banpath in not_allowed_path:
        if banpath[1] == 'c':
            if banpath[0].lower() in path.lower():
                return False
        elif banpath[1] == 'i':
            if banpath[0].lower() == path.lower():
                return False
    return True
# Вставить с заменой файлы в баззу данных , берёт ид, путь до спрайта на который меняет
def set_db_data(content_path, content_id, image_path):
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor() #  UPDATE Content SET Data = data_var WHERE Id = content_id
    compression = cursor.execute("SELECT compression FROM Content WHERE id = ?", [str(content_id)])
    compression = compression.fetchone()[0]
    imagpath = cursor.execute("SELECT path FROM ContentManifest WHERE ContentId = ?", [str(content_id)]).fetchone()[0]
    imagpath = imagpath.lower()
    with open(image_path, 'rb') as f:
        f = f.read()
    if compression != 0:
        f = compress_decompress.compress(f, compression)  
    size = len(f)
    cursor.execute("UPDATE Content SET Data = ? WHERE Id = ?", [f, str(content_id)])
    cursor.execute("UPDATE Content SET Size = ? WHERE Id = ?", [str(size), str(content_id)])
    connection.commit()
    connection.close()
# сохрание по пути до спрайта
def save_current_image(content_path, content_id, compression):
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor()
    data = cursor.execute("SELECT data FROM Content WHERE id = ?", [str(content_id)])
    data = data.fetchone()[0]

    if compression != 0:
        data = compress_decompress.decompress(data)
    imgpath = ctk.filedialog.asksaveasfilename(filetypes=[("PNG","*.png"),("JPG","*.jpg"),("JPEG","*.jpeg")], defaultextension='.png')
    with open(imgpath, 'wb') as f:
        f.write(data)
    connection.close()
# Выдаёт список из bool(ид внутри бд, пути, данные из бд и степени сжатия)
def get_display_sprites(content_path, search_param):
    # empty_folder("/temp")
    path = search_param
    connection = sqlite3.connect(content_path)
    cursor = connection.cursor()
    pairs = []
    content_id = cursor.execute('SELECT ContentId FROM ContentManifest WHERE path LIKE ? AND path LIKE "%.png"', [f'%{path}%']) # Textures/_RMC14/Mobs/Xenonids/Lurker/lurker.rsi/%
    content_id = content_id.fetchall()
    content_id = list(set(content_id))
    for i in content_id:
        compression = cursor.execute("SELECT compression FROM Content WHERE id = ?" , [str(i[0])])
        compression = compression.fetchone()[0]
        data = cursor.execute("SELECT data FROM Content WHERE id="+str(i[0]))
        data = data.fetchone()[0]
        
        instance_path = cursor.execute("SELECT path FROM ContentManifest WHERE ContentId = ?", [str(i[0])])
        instance_path = instance_path.fetchall()[-1][0]

        if compression != 0:
            data = compress_decompress.decompress(data)

        # проверка на запреты
        if check_is_valid(instance_path, data):
            pairs.append((i[0], instance_path, data, compression))
    connection.close()
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
        # какие спрайты смотрим
        self.spriteslocation = 0
        self.spritedelta = 20
        self.pairs = []
        # свойства грида где он будет
        self.griddata = griddata 
        # кнопочка для выбора пути до контента
        self.contentpath_btn = ctk.CTkButton(self, text='Content, path', command = lambda:self.get_file("content_path", [('DB', '*.db')])) # лямбду нужно ставить что бы функция не вызывалась при запуске
        self.contentpath_btn.grid(column = 0, row = 0)
        # sqlite3.connect(content_path).cursor().executescript((remove_check))
        # кнопки для удаления и добавления констрейна
        self.removecheck_btn = ctk.CTkButton(self, text='remove check', command = lambda:sqlite3.connect(self.dict["content_path"]).cursor().executescript((remove_check)).close()) # лямбду нужно ставить что бы функция не вызывалась при запуске
        self.removecheck_btn.grid(column = 1, row = 0)
        self.addcheck_btn = ctk.CTkButton(self, text='add check', command = lambda:sqlite3.connect(self.dict["content_path"]).cursor().executescript((add_check)).close()) # лямбду нужно ставить что бы функция не вызывалась при запуске
        self.addcheck_btn.grid(column = 2, row = 0)
        # создаём фрейм чисто для спрайтов
        self.imageframe = ctk.CTkScrollableFrame(master=self, width=800, height=600)
        self.imageframe.grid(column = 0, row = 3, columnspan = 3)
        # кнопки для смены списка
        self.moveup_btn = ctk.CTkButton(self, text='+', command = lambda:self.change_spriteslocation("+"))
        self.moveup_btn.grid(column = 0, row = 4)
        self.movedown_btn = ctk.CTkButton(self, text='-', command = lambda:self.change_spriteslocation("-"))
        self.movedown_btn.grid(column = 2, row = 4)
        # путь до спрайта
        self.spritepath = ctk.CTkLabel(self, text='')
        self.spritepath.grid(column = 0, row = 5, columnspan = 3)
        # создания ввод парамтров поиска
        self.entry = ctk.CTkEntry(master=self, width=400, height=50)
        self.entry.grid(row=1, column=0, columnspan = 3)
        self.entry.bind("<Return>", command=lambda e:(self.show_on_enter(e, 0, self.spritedelta)))
    # показ при нажатии на ентер
    def show_on_enter(self, e, startx, endx):
        self.spriteslocation = 0
        self.pairs = get_display_sprites(self.dict["content_path"], self.entry.get()) # data = image
        self.clear_frame(self.imageframe)
        self.show_sprites(e, startx, endx)
    #  удаление виджетов в фрейме
    def clear_frame(e, frame):
        for widget in frame.winfo_children():
            widget.destroy()
    # смена self.spriteslocation
    def change_spriteslocation(self, n):
        if n == "+" and self.spriteslocation < len(self.pairs)-self.spritedelta:
            self.spriteslocation += self.spritedelta
        elif self.spriteslocation - self.spritedelta >= 0:
            self.spriteslocation -= self.spritedelta
        self.clear_frame(self.imageframe)
        self.show_sprites(None, self.spriteslocation, self.spriteslocation+self.spritedelta)
    # получаем файлы(фото для смены и путь до контента)
    def get_file(self, key, filetypes):
        self.dict[key] = ctk.filedialog.askopenfilename(filetypes=filetypes)
    # смена текста пути спрайтов
    def change_spt_path_text(self, e, path):
        self.spritepath.configure(text=path)
    # смена или скачивание спрайтов при нажатиит на кнопку
    def change_spr(self, content_id, path, compression):
        msg = CTkMessagebox(title="", message="Download or Change?", icon="question", option_3="Download", option_2="Change", option_1="Copy path to clipboard")
        response = msg.get()
        if response == "Change":
            self.get_file("change_image_to_path", [("PNG","*.png"),("JPG","*.jpg"),("JPEG","*.jpeg")])
            img_file = self.dict["change_image_to_path"]
            if img_file != None and img_file != '':
                set_db_data(self.dict["content_path"], content_id, img_file)
        elif response == "Download":
            save_current_image(self.dict["content_path"], content_id, compression)
        elif response == "Copy path to clipboard":
            pyperclip.copy(path)
            CTkMessagebox(title="Done!", message="Path is copied")
    # Показ спрайтов
    def show_sprites(self, e, startx, endx):
        if self.dict["content_path"] == "":
            pass 
        else:
            imagesize = (self.contentpath_btn.cget("width"), self.contentpath_btn.cget("width"))
            pairs = self.pairs[startx:endx]
            n = len(pairs)
            lenx = self.imageframe.winfo_width()//imagesize[0]
            leny = n//lenx+1
            for row in range(leny):
                for column in range(lenx):
                    if not row*lenx + column < n:
                        break
                    else:
                        pair = pairs[row*lenx + column]
                        content_id, path, data, compression = pair[0], pair[1], pair[2], pair[3]
                        image = Image.open(io.BytesIO(data)) 
                        self.imageframe.img_btn = ctk.CTkButton(self.imageframe, image=ctk.CTkImage(light_image=image, dark_image=image, size=imagesize), text = "", fg_color='transparent', command= lambda content_id = content_id, path = path, compression=compression:self.change_spr(content_id, path, compression))
                        self.imageframe.img_btn.bind('<Enter>', lambda e, x=path:(self.change_spt_path_text(e, x)), add='+')
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
        # текст в углу
        self.gitlink = ctk.CTkEntry(self,fg_color="transparent", width=500, border_width=0, font=(ctk.CTkFont, 15))
        self.gitlink.insert(0, 'https://github.com/sozork/SS14-Change-Sprites-customtkinter-rewrite')
        self.gitlink.configure(state='readonly')
        self.gitlink.grid(sticky="sw")
# запуск 
if __name__ == "__main__":
    app = App()
    app.mainloop()