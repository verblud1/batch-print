#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
from PIL import Image
import glob
import time
from tkinter import Tk, simpledialog, messagebox
import getpass
import shutil
from datetime import datetime

def setup_printer():
    """Настройка принтера (ваш оригинальный код)"""
    try:
        print("Настраиваю принтер LBP6020...")
        
        # Добавление принтера в систему
        subprocess.run([
            '/usr/sbin/lpadmin',
            '-p', 'LBP6020',
            '-m', 'CNCUPSLBP6020CAPTK.ppd',
            '-v', 'ccp://localhost:59687',
            '-E'
        ], check=True)
        
        # Настройка драйвера ccpd
        subprocess.run([
            'sudo', '/usr/sbin/ccpdadmin',
            '-p', 'LBP6020',
            '-o', '/dev/usb/lp0'
        ], check=True)
        
        # Перезапуск службы ccpd
        subprocess.run(['sudo', '/etc/init.d/ccpd', 'restart'], check=True)
        
        print("Настройка принтера LBP6020 завершена")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Ошибка настройки принтера: {e}")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return False

def create_a4_with_two_images(images, output_path, page_number, is_front=True):
    """Создает A4 страницу с двумя изображениями"""
    # Размер A4 в пикселях при 300 DPI
    A4_WIDTH = 2480  # 210mm * 300/25.4
    A4_HEIGHT = 3508  # 297mm * 300/25.4
    
    # Размер для каждого изображения (половина страницы минус отступы)
    IMG_WIDTH = A4_WIDTH - 200  # 100px отступ с каждой стороны
    IMG_HEIGHT = (A4_HEIGHT // 2) - 150  # по 75px отступ сверху/снизу для каждого изображения
    
    # Создаем новое белое изображение A4
    a4_image = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    
    positions = []
    if is_front:
        positions = [(100, 75), (100, A4_HEIGHT//2 + 75)]  # Верх и низ для лицевой стороны
    else:
        positions = [(100, 75), (100, A4_HEIGHT//2 + 75)]  # Тоже верх и низ для обратной стороны
    
    for i, (img_path, pos) in enumerate(zip(images, positions)):
        try:
            img = Image.open(img_path)
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            # Масштабируем изображение с сохранением пропорций
            img.thumbnail((IMG_WIDTH, IMG_HEIGHT), Image.Resampling.LANCZOS)
            
            # Вычисляем позицию для центрирования
            x_offset = pos[0] + (IMG_WIDTH - img.width) // 2
            y_offset = pos[1] + (IMG_HEIGHT - img.height) // 2
            
            # Вставляем изображение на A4 страницу
            a4_image.paste(img, (x_offset, y_offset))
            
            img.close()
            
        except Exception as e:
            print(f"Ошибка обработки {img_path}: {e}")
    
    # Сохраняем временный файл
    temp_file = f"{output_path}/page_{page_number:03d}_{'front' if is_front else 'back'}.pdf"
    a4_image.save(temp_file, 'PDF', resolution=300.0)
    
    return temp_file

def print_pdf(pdf_file):
    """Печатает PDF файл"""
    try:
        subprocess.run(['lp', '-d', 'LBP6020', pdf_file], check=True)
        print(f"Отправлено на печать: {pdf_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка печати: {e}")
        return False

def get_user_confirmation(message):
    """Получает подтверждение от пользователя"""
    root = Tk()
    root.withdraw()  # Скрываем основное окно
    
    # Создаем диалоговое окно
    result = messagebox.askyesno("Подтверждение", message)
    root.destroy()
    
    return result

def create_printed_directory_with_date(folder_path):
    """Создает папку для сохранения напечатанных файлов с текущей датой"""
    # Получаем текущую дату в формате DD.MM.YYYY
    current_date = datetime.now().strftime("%d.%m.%Y")
    printed_dir_name = f"printed {current_date}"
    printed_dir = os.path.join(folder_path, printed_dir_name)
    
    # Если папка уже существует, используем ее
    if os.path.exists(printed_dir):
        print(f"Используется существующая папка: {printed_dir}")
    else:
        # Создаем новую папку с датой
        os.makedirs(printed_dir, exist_ok=True)
        print(f"Создана новая папка с текущей датой: {printed_dir}")
    
    return printed_dir

def setup_archive_directory(folder_path):
    """Настраивает папку archive для долгосрочного хранения"""
    archive_dir = os.path.join(folder_path, "archive")
    
    # Если папка archive существует
    if os.path.exists(archive_dir):
        print(f"Найдена папка archive: {archive_dir}")
    else:
        # Создаем папку archive
        os.makedirs(archive_dir, exist_ok=True)
        print(f"Создана папка archive: {archive_dir}")
    
    return archive_dir

def save_to_printed_directory(pdf_file, printed_dir, page_number, side):
    """Сохраняет копию PDF файла в папку printed с датой"""
    try:
        # Создаем имя файла с временной меткой и номером страницы
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"page_{page_number:03d}_{side}_{timestamp}.pdf"
        destination = os.path.join(printed_dir, filename)
        
        # Копируем файл
        shutil.copy2(pdf_file, destination)
        print(f"Сохранена копия в printed: {destination}")
        return destination
    except Exception as e:
        print(f"Ошибка при сохранении в printed: {e}")
        return None

def save_to_archive(pdf_file, archive_dir, page_number, side):
    """Сохраняет копию PDF файла в папку archive"""
    try:
        # Создаем имя файла с датой и временем
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"page_{page_number:03d}_{side}_{timestamp}.pdf"
        destination = os.path.join(archive_dir, filename)
        
        # Копируем файл
        shutil.copy2(pdf_file, destination)
        print(f"Сохранена копия в archive: {destination}")
        return destination
    except Exception as e:
        print(f"Ошибка при сохранении в archive: {e}")
        return None

def move_printed_png_to_archive(png_files, archive_dir):
    """Перемещает напечатанные PNG файлы в подпапку archive"""
    try:
        # Создаем подпапку для PNG в archive
        png_archive_dir = os.path.join(archive_dir, "printed_png")
        os.makedirs(png_archive_dir, exist_ok=True)
        
        moved_count = 0
        for png_file in png_files:
            try:
                # Получаем имя файла
                filename = os.path.basename(png_file)
                destination = os.path.join(png_archive_dir, filename)
                
                # Если файл уже существует, добавляем временную метку
                if os.path.exists(destination):
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"
                    destination = os.path.join(png_archive_dir, filename)
                
                # Перемещаем файл
                shutil.move(png_file, destination)
                moved_count += 1
                print(f"Перемещен PNG в archive: {filename}")
                
            except Exception as e:
                print(f"Ошибка при перемещении {png_file}: {e}")
        
        print(f"Всего перемещено PNG файлов: {moved_count}")
        return moved_count
        
    except Exception as e:
        print(f"Ошибка при создании папки для PNG: {e}")
        return 0

def main():
    # Запрашиваем путь к папке с изображениями
    root = Tk()
    root.withdraw()
    
    # Для Red OS можно использовать стандартные пути
    default_path = "/home/comp_step/Desktop/database_screens"
    if not os.path.exists(default_path):
        default_path = f"/home/{getpass.getuser()}"
    
    folder_path = simpledialog.askstring(
        "Выбор папки",
        f"Введите путь к папке с PNG файлами:",
        initialvalue=default_path
    )
    root.destroy()
    
    if not folder_path or not os.path.exists(folder_path):
        print("Папка не существует или не указана")
        return
    
    # Получаем список PNG файлов
    png_files = sorted(glob.glob(os.path.join(folder_path, "*.png")))
    
    if not png_files:
        print("PNG файлы не найдены в указанной папке")
        return
    
    total_files = len(png_files)
    print(f"Найдено {total_files} PNG файлов")
    
    # Создаем папку для сохранения напечатанных файлов с текущей датой
    printed_dir = create_printed_directory_with_date(folder_path)
    
    # Настраиваем папку archive
    archive_dir = setup_archive_directory(folder_path)
    
    # Настраиваем принтер
    if not setup_printer():
        print("Продолжаем без настройки принтера...")
    
    # Создаем временную директорию для PDF файлов
    with tempfile.TemporaryDirectory() as temp_dir:
        page_count = 0
        printed_png_files = []  # Список напечатанных PNG файлов
        
        # Обрабатываем файлы по 4 на лист (2 на лицевой, 2 на обратной стороне)
        for i in range(0, total_files, 4):
            page_count += 1
            print(f"\nОбрабатываю лист {page_count}...")
            
            # Получаем 4 файла для текущего листа
            current_files = png_files[i:i+4]
            front_files = current_files[:2]
            back_files = current_files[2:4] if len(current_files) > 2 else []
            
            # Добавляем файлы в список напечатанных
            printed_png_files.extend(current_files)
            
            # Создаем PDF для лицевой стороны
            if front_files:
                front_pdf = create_a4_with_two_images(
                    front_files, temp_dir, page_count, is_front=True
                )
                
                # Сохраняем копию в папку printed с датой
                saved_printed = save_to_printed_directory(front_pdf, printed_dir, page_count, "front")
                
                # Сохраняем копию в папку archive
                if saved_printed:
                    save_to_archive(saved_printed, archive_dir, page_count, "front")
                
                # Печатаем лицевую сторону
                print(f"Печатаю лицевую сторону листа {page_count}...")
                if print_pdf(front_pdf):
                    # Ждем завершения печати
                    time.sleep(5)
            
            # Если есть обратная сторона
            if back_files:
                # Ждем подтверждения пользователя
                print(f"\nЛист {page_count}: Лицевая сторона напечатана.")
                print("Пожалуйста:")
                print("1. Переверните напечатанный лист")
                print("2. Вставьте его обратно в принтер той же стороной вверх")
                print("3. Нажмите OK для продолжения")
                
                if get_user_confirmation(
                    f"Лист {page_count}:\n"
                    "1. Переверните напечатанный лист\n"
                    "2. Вставьте его обратно в принтер\n"
                    "3. Нажмите OK для печати обратной стороны"
                ):
                    # Создаем PDF для обратной стороны
                    back_pdf = create_a4_with_two_images(
                        back_files, temp_dir, page_count, is_front=False
                    )
                    
                    # Сохраняем копию в папку printed с датой
                    saved_printed = save_to_printed_directory(back_pdf, printed_dir, page_count, "back")
                    
                    # Сохраняем копию в папку archive
                    if saved_printed:
                        save_to_archive(saved_printed, archive_dir, page_count, "back")
                    
                    # Печатаем обратную сторону
                    print(f"Печатаю обратную сторону листа {page_count}...")
                    print_pdf(back_pdf)
                    
                    # Ждем завершения печати
                    time.sleep(5)
                else:
                    print("Печать прервана пользователем")
                    break
            else:
                print(f"Лист {page_count}: Только лицевая сторона (нечетное количество изображений)")
            
            print(f"Лист {page_count} завершен")
        
        print(f"\nГотово! Обработано {min(page_count, (total_files + 3) // 4)} листов")
        print(f"Все PDF файлы сохранены в папке: {printed_dir}")
        print(f"Архивные копии сохранены в папке: {archive_dir}")
        
        # Создаем README файл с информацией о печати
        create_readme_file(printed_dir, total_files, page_count, archive_dir)
        
        # Предлагаем переместить напечатанные PNG файлы в архив
        if printed_png_files:
            print(f"\nНапечатано {len(printed_png_files)} PNG файлов.")
            if get_user_confirmation(
                f"Переместить напечатанные PNG файлы ({len(printed_png_files)} шт.)\n"
                "в подпапку archive/printed_png?"
            ):
                moved_count = move_printed_png_to_archive(printed_png_files, archive_dir)
                print(f"Перемещено {moved_count} PNG файлов в архив")
            else:
                print("PNG файлы оставлены на месте")

def create_readme_file(printed_dir, total_files, total_pages, archive_dir):
    """Создает информационный файл о печати"""
    readme_path = os.path.join(printed_dir, "README.txt")
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ИНФОРМАЦИЯ О ПЕЧАТИ\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Дата печати: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Папка печати: {os.path.basename(printed_dir)}\n")
        f.write(f"Папка архива: {os.path.basename(archive_dir)}\n")
        f.write(f"Общее количество изображений: {total_files}\n")
        f.write(f"Количество листов: {total_pages}\n")
        f.write(f"Печать выполнена: по 2 изображения на сторону A4\n")
        f.write(f"Папка с исходными изображениями: {os.path.dirname(printed_dir)}\n\n")
        
        f.write("СОХРАНЕННЫЕ КОПИИ:\n")
        f.write(f"1. Папка printed: {printed_dir}\n")
        f.write("   - Временное хранение PDF по датам\n")
        f.write(f"2. Папка archive: {archive_dir}\n")
        f.write("   - Долгосрочное хранение всех PDF\n")
        f.write("   - Подпапка printed_png: исходные PNG файлы (по запросу)\n\n")
        
        f.write("ИМЕНА ФАЙЛОВ:\n")
        f.write("Формат: page_XXX_front/back_ГГГГММДД_ЧЧММСС.pdf\n")
        f.write("Пример: page_001_front_20241222_143022.pdf\n\n")
        
        f.write("ПРИМЕЧАНИЕ:\n")
        f.write("1. Папка printed названа по дате печати\n")
        f.write("2. Папка archive содержит все напечатанные файлы за все время\n")
        f.write("3. После печати можно переместить PNG файлы в archive/printed_png\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("АВТОМАТИЧЕСКИ СОЗДАНО СКРИПТОМ ПЕЧАТИ\n")
        f.write("=" * 60 + "\n")

if __name__ == "__main__":
    # Проверяем зависимости
    try:
        from PIL import Image
    except ImportError:
        print("Установите необходимые библиотеки:")
        print("sudo pip3 install Pillow")
        print("sudo dnf install python3-tkinter")
        sys.exit(1)
    
    main()
