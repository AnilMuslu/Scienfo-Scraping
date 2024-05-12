import requests
import firebase_admin
import tempfile
import os

from dotenv import load_dotenv
from datetime import timedelta
from bs4 import BeautifulSoup
from firebase_admin import credentials
from firebase_admin import storage
from firebase_admin import firestore

load_dotenv()

# Firebase kimlik bilgilerini yükleme
cred_path = os.path.join(os.getcwd(), "creds.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': os.environ["STORAGE_BUCKET"]
})

bucket = storage.bucket()
db = firestore.client()

project_directory = os.path.dirname(os.path.abspath(__file__))

# Ziyaret edilen URL'leri takip etmek için
visited_urls = set()

total_images_saved = 0

def scrape_and_store_data(url):
    global total_images_saved

    # URL'yi ziyaret edildi olarak işaretleme
    visited_urls.add(url)

    # URL'ye istek gönderip sayfayı alma
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Görüntü etiketi seçici
    image_selector = 'img'

    # <h4> başlık etiketi seçici
    h4_headings = soup.find_all('h4')

    # Sayfadaki tüm görüntüler için döngü
    for image in soup.select(image_selector):
        image_url = image.get('src')
        width = int(image.get('width', 0))
        height = int(image.get('height', 0))

        # Boyut filtresi
        if width < 100 or height < 100:
            continue

        # Başlıkları işleme ve yazdırma
        for heading in h4_headings:
            content = heading.text.strip()
            parts = content.split(',')
            category = parts[0].strip()
            user_profile = parts[1].strip() if len(parts) > 1 else ''

        # Geçici dosya için bir dizin oluşturma
        temp_directory = os.path.join(project_directory, 'temp')
        os.makedirs(temp_directory, exist_ok=True)

        # Geçici dosya oluşturma
        with tempfile.NamedTemporaryFile(dir=temp_directory, delete=False) as temp_file:
            # Görüntüyü indirme ve geçici dosyaya kaydetme
            image_response = requests.get(image_url)
            temp_file.write(image_response.content)

            # Görüntüyü Firebase Storage'a yükleme
            blob = bucket.blob(temp_file.name)
            blob.upload_from_filename(temp_file.name)

            image_firestore_url = blob.generate_signed_url(timedelta(seconds=999999999), method='GET')

            # Firestore'a veriyi kaydedin
            data = {
                'blog': url,
                'image_url': image_firestore_url,
                'category': category,
                'user_profile': user_profile
            }
            db.collection('images').add(data)

            total_images_saved += 1

            print('Blog:', url)
            print('Görsel URL:', image_firestore_url)
            print('Kategori:', category)
            print('Kullanıcı Profili:', user_profile)
            print('Görüntü Firestore\'a kaydedildi.')
            print('------------------------')

    # Bağlantıları alma
    links = soup.select('a[href]')
    for link in links:
        href = link.get('href')
        if href.startswith(blog_url) and href not in visited_urls and not href.endswith("#comments"):
            scrape_and_store_data(href)

def cleanup_temp_files():
    temp_directory = os.path.join(project_directory, 'temp')
    for filename in os.listdir(temp_directory):
        file_path = os.path.join(temp_directory, filename)
        os.remove(file_path)
    os.rmdir(temp_directory)
    print("Geçici olarak kullanılan temp klasörü temizlendi")

if __name__ == '__main__':
    # Blog sitesinin URL'si
    blog_url = "https://scienfoapp.blogspot.com/"

    # Web scraping ve veri kaydetme
    scrape_and_store_data(blog_url)

    print('Toplam Kaydedilen Görsel Sayısı:', total_images_saved)

    cleanup_temp_files()