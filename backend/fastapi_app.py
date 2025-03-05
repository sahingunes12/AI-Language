from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from .database import get_db, Item, User, UserProfile, init_db, UserActivity
from .auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
import pandas as pd
import wikipediaapi
from langdetect import detect
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import random
import http.client
import json
import os
from dotenv import load_dotenv

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# Veritabanı tablolarını oluştur
init_db()

# CORS ayarlarını ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Gerçek uygulamada güvenlik için belirli origin'leri belirtin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    
    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class UserProfileCreate(BaseModel):
    learning_purpose: str
    daily_minutes: int

class UserProfileResponse(BaseModel):
    id: int
    learning_purpose: str
    daily_minutes: int
    created_at: str
    
    class Config:
        orm_mode = True

class ActivityCreate(BaseModel):
    activity_type: str
    duration: int
    notes: Optional[str] = None

class ActivityResponse(BaseModel):
    id: int
    activity_type: str
    duration: int
    notes: Optional[str]
    completed_at: str
    
    class Config:
        orm_mode = True

# İlk çalıştırmada NLTK verilerini indir
try:
    # Tokenizasyon için gerekli verileri indir
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')
    
    # İspanyolca için ek kaynaklar
    nltk.download('spanish')
except Exception as e:
    print(f"NLTK veri indirme hatası: {str(e)}")

# Örnek seviyeye göre hazır metinler
predefined_texts = {
    "a1": [
        {
            "title": "Mi Familia", 
            "text": "Me llamo Juan. Tengo una familia pequeña. Mi padre se llama Carlos y mi madre se llama María. Tengo un hermano y una hermana. Mi hermano es mayor y mi hermana es menor. Vivimos en una casa bonita con un perro. El perro se llama Toby. Me gusta mucho mi familia.",
            "source": "Hazır Metin"
        },
        # Diğer A1 metinleri
    ],
    "a2": [
        # A2 metinleri
    ],
    # Diğer seviyeler
}

# .env dosyasından API anahtarını yükle
load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "scrapedino.p.rapidapi.com"

# Kelime çevirilerini önbelleğe alan bir sözlük
translation_cache = {}

# Authentication routes
@app.post("/api/register")
async def register_user_json(user_data: dict):
    try:
        # Kullanıcı verilerini kontrol edelim
        if "email" not in user_data or "username" not in user_data or "password" not in user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, kullanıcı adı ve şifre gereklidir"
            )
            
        # Veritabanı bağlantısı
        db = next(get_db())
        
        # Kullanıcının zaten var olup olmadığını kontrol et
        existing_user = db.query(User).filter(
            (User.email == user_data["email"]) | (User.username == user_data["username"])
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kullanıcı zaten kayıtlı"
            )
        
        # Yeni kullanıcı oluştur
        hashed_password = get_password_hash(user_data["password"])
        db_user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {"message": "Kullanıcı başarıyla oluşturuldu"}
    
    except HTTPException as he:
        # Zaten tanımlanmış HTTP hataları
        raise he
    except Exception as e:
        # Hata günlüğü
        print(f"Register error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

@app.post("/api/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.post("/api/login")
async def login_json(user_data: dict):
    try:
        # Önce veritabanına erişim sağlayalım
        db = next(get_db())
        
        # Kullanıcı verilerini kontrol edelim
        if "username" not in user_data or "password" not in user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kullanıcı adı ve şifre gereklidir"
            )
        
        username = user_data["username"]
        password = user_data["password"]
        
        # Kimlik doğrulama
        user = authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz kullanıcı adı veya şifre",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Token oluşturma
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "username": user.username}
        
    except Exception as e:
        # Hata günlüğü
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Routes
@app.get("/api/items", response_model=List[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return items

@app.post("/api/items", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/profile", response_model=UserProfileResponse)
async def create_profile(
    profile_data: UserProfileCreate, 
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        # Token'dan kullanıcı kimliğini çıkarma
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz kimlik bilgileri"
            )
        
        # Kullanıcıyı bulma
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı"
            )
        
        # Kullanıcının mevcut bir profili var mı kontrol et
        if user.profile:
            # Profili güncelle
            user.profile.learning_purpose = profile_data.learning_purpose
            user.profile.daily_minutes = profile_data.daily_minutes
            db.commit()
            db.refresh(user.profile)
            return user.profile
        
        # Yeni profil oluştur
        profile = UserProfile(
            user_id=user.id,
            learning_purpose=profile_data.learning_purpose,
            daily_minutes=profile_data.daily_minutes,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return profile
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

@app.get("/api/profile", response_model=UserProfileResponse)
async def get_profile(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        # Token'dan kullanıcı kimliğini çıkarma
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz kimlik bilgileri"
            )
        
        # Kullanıcıyı bulma
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı"
            )
        
        # Kullanıcı profilini bul
        if not user.profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil henüz oluşturulmamış"
            )
        
        return user.profile
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Aktivite kaydetme endpoint'i
@app.post("/api/activities", response_model=ActivityResponse)
async def create_activity(
    activity: ActivityCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        # Token'dan kullanıcı kimliğini çıkarma
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Yeni aktivite oluştur
        new_activity = UserActivity(
            user_id=user.id,
            activity_type=activity.activity_type,
            duration=activity.duration,
            notes=activity.notes,
            completed_at=datetime.now().strftime("%Y-%m-%d")
        )
        
        db.add(new_activity)
        db.commit()
        db.refresh(new_activity)
        
        return new_activity
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Activity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Aktiviteleri sorgulama endpoint'i
@app.get("/api/activities", response_model=List[ActivityResponse])
async def get_activities(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    try:
        # Token'dan kullanıcı kimliğini çıkarma
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Aktiviteleri sorgula
        query = db.query(UserActivity).filter(UserActivity.user_id == user.id)
        
        if start_date:
            query = query.filter(UserActivity.completed_at >= start_date)
        if end_date:
            query = query.filter(UserActivity.completed_at <= end_date)
        
        activities = query.order_by(UserActivity.completed_at.desc()).all()
        
        return activities
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Get activities error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Aktivite özeti endpoint'i
@app.get("/api/activities/summary")
async def get_activity_summary(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    period: Optional[str] = "week"  # week, month, year
):
    try:
        # Token'dan kullanıcı kimliğini çıkarma
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Tarih aralığını belirle
        today = datetime.now().date()
        
        if period == "week":
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        elif period == "month":
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        elif period == "year":
            start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        else:
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        
        end_date = today.strftime("%Y-%m-%d")
        
        # Aktiviteleri sorgula
        activities = db.query(UserActivity).filter(
            UserActivity.user_id == user.id,
            UserActivity.completed_at >= start_date,
            UserActivity.completed_at <= end_date
        ).all()
        
        # Aktivite türlerine göre toplam süreleri hesapla
        summary = {
            "konuşma": 0,
            "yazma": 0,
            "dinleme": 0,
            "okuma": 0,
            "gramer öğrenme": 0,
            "kelime dağarcığı geliştirme": 0,
            "total": 0
        }
        
        for activity in activities:
            activity_type = activity.activity_type.lower()
            if activity_type in summary:
                summary[activity_type] += activity.duration
                summary["total"] += activity.duration
        
        # Günlük ortalama süreyi hesapla
        days = (today - datetime.strptime(start_date, "%Y-%m-%d").date()).days or 1
        summary["daily_average"] = summary["total"] / days
        
        # Öneriler oluştur
        recommendations = []
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        
        if profile:
            target_activity = profile.learning_purpose.lower()
            target_minutes = profile.daily_minutes
            
            # Hedef aktivite kontrolü
            if target_activity in summary:
                daily_avg = summary[target_activity] / days
                
                if daily_avg < target_minutes * 0.5:
                    recommendations.append(f"{target_activity.capitalize()} hedefinize ulaşmak için daha fazla zaman ayırmalısınız.")
            
            # Aktivite dengesi
            if summary["total"] > 0:
                for activity_type, minutes in summary.items():
                    if activity_type not in ["total", "daily_average"]:
                        percentage = (minutes / summary["total"]) * 100 if summary["total"] > 0 else 0
                        
                        if percentage < 10 and minutes < 30:
                            recommendations.append(f"{activity_type.capitalize()} pratiği eksik görünüyor, daha fazla zaman ayırın.")
            
            # Çalışma rutini
            if summary["total"] < 30:
                recommendations.append("Düzenli çalışma alışkanlığı geliştirmelisiniz. Her gün en az 15 dakika ayırın.")
            
            # Başarı durumu
            if summary["daily_average"] > target_minutes * 1.2:
                recommendations.append("Harika ilerliyorsunuz! Hedeflerinizi biraz daha yükseltmeyi düşünebilirsiniz.")
        
        return {
            "summary": summary,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "recommendations": recommendations
        }
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Summary error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# İspanyolca metin alma endpoint'i
@app.get("/api/reading/text")
async def get_reading_text(
    token: str = Depends(oauth2_scheme),
    topic: Optional[str] = None,
    level: str = "b1"  # a1, a2, b1, b2, c1, c2
):
    try:
        # Kullanıcı doğrulama
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        # Hazır metin kullanılabilir mi kontrol et
        if level in predefined_texts and random.random() < 0.7:  # %70 olasılıkla hazır metin kullan
            text_data = random.choice(predefined_texts[level])
            title = text_data["title"]
            text = text_data["text"]
            source = text_data["source"]
            source_url = "#"  # Hazır metinler için kaynak URL yok
        else:
            # Wikipedia API'yi başlat
            wiki_wiki = wikipediaapi.Wikipedia('tr.wikipedia.org', 'es')
            
            # Seviyeye göre konuları belirle
            topics = {
                "a1": [
                    "Familia", "Casa", "Comida", "Color", "Animal", 
                    "Número", "Día", "Mes", "Hora", "Fruta"
                ],
                "a2": [
                    "Deporte", "Escuela", "Música", "Tiempo", "Salud",
                    "Ropa", "Viaje", "Restaurante", "Compras", "Hobby"
                ],
                "b1": [
                    "Historia de España", "Geografía de España", "Cultura de México",
                    "Turismo en España", "Gastronomía española", "Deportes en España",
                    "Parques nacionales", "Fiestas populares", "Tradiciones", "Música española"
                ],
                "b2": [
                    "Literatura española", "Arte español", "Cine español", 
                    "Política de España", "Medio ambiente", "Sociedad española",
                    "Educación en España", "Historia de México", "Cocina latinoamericana",
                    "Religión en España"
                ],
                "c1": [
                    "Filosofía española", "Ciencia en España", "Economía de España",
                    "Arquitectura española", "Literatura latinoamericana",
                    "Historia del arte español", "Política internacional española",
                    "Empresas españolas", "Sistema político español", "Derecho español"
                ],
                "c2": [
                    "Arqueología en España", "Lingüística española", "Antropología española",
                    "Historia de la filosofía española", "Economía global",
                    "Política latinoamericana", "Corrientes literarias españolas",
                    "Movimientos artísticos españoles", "Crítica social", "Academia española"
                ]
            }
            
            # Konu belirtilmemişse, seviyeye göre rastgele bir konu seç
            if not topic:
                selected_topic = random.choice(topics.get(level, topics["b1"]))
            else:
                selected_topic = topic
            
            # Wikipedia'dan sayfayı al
            page = wiki_wiki.page(selected_topic)
            
            if not page.exists():
                # Konu bulunamadıysa rastgele bir konu seç
                selected_topic = random.choice(topics.get(level, topics["b1"]))
                page = wiki_wiki.page(selected_topic)
                
                if not page.exists():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Konu bulunamadı"
                    )
            
            # Tam metni al
            full_text = page.text[:8000]  # Metni sınırla
            
            # Metin uzunluğunu seviyeye göre ayarla
            text_length = {
                "a1": min(500, len(full_text)),    # Çok kısa ve basit
                "a2": min(800, len(full_text)),    # Kısa ve temel
                "b1": min(1500, len(full_text)),   # Orta uzunluk
                "b2": min(2500, len(full_text)),   # Orta-uzun
                "c1": min(4000, len(full_text)),   # Uzun ve karmaşık
                "c2": min(8000, len(full_text))    # Çok uzun ve detaylı
            }
            
            text = full_text[:text_length.get(level, text_length["b1"])]
            
            # Özet uzunluğunu da seviyeye göre ayarla
            summary_length = {
                "a1": 2,  # Sadece 2 cümle
                "a2": 3,  # 3 cümle
                "b1": 4,  # 4 cümle
                "b2": 5,  # 5 cümle
                "c1": 6,  # 6 cümle
                "c2": 8   # 8 cümle
            }
            
            # Özet oluştur
            try:
                # Seviyeye göre uyarlanmış özet uzunluğu
                sentence_count = summary_length.get(level, 4)
                summary = simple_summarize(text, sentence_count=sentence_count)
            except Exception as e:
                # Özet oluşturma başarısız olursa, daha basit bir özet oluştur
                sentences = text.split('. ')
                summary = '. '.join(sentences[:3]) + '.'
            
            # Bilinmeyen kelimeler için temel kelime listesi (İspanyolca için)
            basic_spanish_words = {"el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "porque", "como", "qué", "quién", "cuándo", "dónde", "por", "para", "con", "sin", "en", "de", "a", "al", "del", "es", "son", "estar", "ser", "haber", "tener", "hacer", "ir", "venir", "ver", "oír", "decir", "hablar", "comer", "beber", "dormir", "vivir", "trabajar", "estudiar", "sí", "no", "tal vez", "quizás", "hoy", "ayer", "mañana", "ahora", "luego", "después", "antes", "siempre", "nunca", "todo", "nada", "mucho", "poco", "más", "menos", "bien", "mal"}
            
            # Metindeki kelimeleri analiz et
            words = simple_tokenize(text.lower())
            unique_words = set([word for word in words if word.isalpha()])
            
            # "Bilinmeyen" kelimeler (basit kelime listesinde olmayan kelimeler)
            unknown_words = list(unique_words - basic_spanish_words)
            
            # Seviyeye göre gösterilecek bilinmeyen kelime sayısını ayarla
            unknown_word_count = {
                "a1": 5,   # Çok az
                "a2": 8,   # Az
                "b1": 12,  # Orta
                "b2": 15,  # Biraz fazla
                "c1": 20,  # Fazla
                "c2": 25   # Çok fazla
            }
            
            # Seviyeye göre kelime sayısını sınırla
            max_words = unknown_word_count.get(level, 15)
            unknown_words = unknown_words[:max_words]
            
            # Kelime anlamları için basit bir sözlük oluştur (gerçek bir API ile değiştirilecek)
            word_meanings = {}
            
            # Fiil listesi
            verbs = []
            # İsim listesi
            nouns = []
            
            for word in unknown_words:
                # API ile çeviri yap
                turkish_meaning = translate_word_api(word, source_lang="es", target_lang="tr")
                
                # Fiil/isim kontrolü yap
                if word.endswith(('ar', 'er', 'ir')) and len(word) > 2:
                    verbs.append(word)
                    word_meanings[word] = turkish_meaning + " (fiil)"
                else:
                    nouns.append(word)
                    word_meanings[word] = turkish_meaning + " (isim/sıfat)"
            
            title = page.title
            source = "Wikipedia"
            source_url = page.fullurl
        return {
            "title": title,
            "url": source_url,
            "text": text,
            "summary": summary,
            "level": level,
            "unknown_words": unknown_words,
            "verbs": verbs,  # Fiiller
            "nouns": nouns,  # İsimler/Sıfatlar
            "word_meanings": word_meanings,
            "source": source
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Reading error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Dil algılama endpoint'i
@app.post("/api/reading/detect-language")
async def detect_language(
    text_data: dict,
    token: str = Depends(oauth2_scheme)
):
    try:
        # Kullanıcı doğrulama
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if "text" not in text_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Metin alanı gereklidir"
            )
        
        text = text_data["text"]
        
        # Dil algılama
        try:
            detected_language = detect(text)
        except:
            detected_language = "unknown"
        
        return {
            "language": detected_language
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Language detection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sunucu hatası: {str(e)}"
        )

# Basit özetleme fonksiyonu
def simple_summarize(text, sentence_count=3):
    sentences = text.split('. ')
    if len(sentences) <= sentence_count:
        return text
    else:
        return '. '.join(sentences[:sentence_count]) + '.'

# Metindeki kelimeleri analiz et
def simple_tokenize(text):
    """Basit kelime tokenizasyon fonksiyonu"""
    return [word.strip('.,;:!?()[]{}"\'-').lower() for word in text.split() if word.strip('.,;:!?()[]{}"\'-')]

# Google Translate API için (ücretli)
# from googletrans import Translator

# Basit çeviri fonksiyonu - gerçek uygulamada API kullanılmalı
def translate_word(word, source_lang="es", target_lang="tr"):
    # Google Translate API yerine basit önceden tanımlanmış çeviriler
    spanish_turkish = {
        "animales": "hayvanlar",
        "constituyen": "oluşturur",
        "reino": "krallık",
        "seres": "varlıklar",
        "vivos": "canlı",
        "eucariotas": "ökaryot",
        "heterótrofos": "heterotrof",
        "pluricelulares": "çok hücreli",
        "tisulares": "dokusal",
        "poríferos": "süngerler",
        "capacidad": "kapasite",
        "movimiento": "hareket",
        "cloroplasto": "kloroplast",
        "excepciones": "istisnalar",
        "chlorotica": "klorotik",
        "celular": "hücresel",
        "desarrollo": "gelişim",
        "embrionario": "embriyonik",
        "blástula": "blastula",
        "determina": "belirler",
        "plan": "plan",
        "corporal": "vücut",
        # Fiiller
        "reúne": "toplar",
        "caracterizan": "karakterize eder",
        "tener": "sahip olmak",
        "atraviesa": "geçer"
    }
    
    # Kelimeyi küçük harfe çevirip temizle
    word = word.lower().strip('.,;:!?()[]{}"\'-')
    
    # Sözlükte varsa çevirisini döndür, yoksa "Çeviri bulunamadı" mesajı döndür
    return spanish_turkish.get(word, "Çeviri bulunamadı")

def translate_word_api(word, source_lang="es", target_lang="tr"):
    """API ile kelime çevirisi yap"""
    # Önbellekte varsa oradan al
    cache_key = f"{word.lower()}_{source_lang}_{target_lang}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Zaten çevirisini bildiğimiz kelimeleri kontrol et
    known_translations = {
        "animales": "hayvanlar",
        "constituyen": "oluşturur",
        "reino": "krallık",
        # ... (diğer çeviriler) 
    }
    
    # Kelime zaten biliniyorsa, çevirisini doğrudan döndür
    if word.lower() in known_translations:
        return known_translations[word.lower()]
    
    # API'ye bağlan
    try:
        conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
        
        # Gerçek bir çeviri servisi URL'si - örnek: Google Translate URL'si
        # Bu örnek yapmacık bir URL; gerçek implementasyonda bu URL'yi bir çeviri
        # servisinin URL'si ile değiştirmeniz gerekecek
        target_url = f"https://translate.google.com/?sl={source_lang}&tl={target_lang}&text={word}"
        
        payload = json.dumps({
            "method": "GET",
            "url": target_url,
            "headers": {},
            "queryParams": {},
            "bodyType": "raw",
            "body": ""
        })
        
        headers = {
            'x-rapidapi-key': RAPIDAPI_KEY,
            'x-rapidapi-host': RAPIDAPI_HOST,
            'Content-Type': "application/json"
        }
        
        conn.request("POST", "/js", payload, headers)
        
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        
        # Burada data içindeki çeviriyi çıkaran bir parser yazmanız gerekecek
        # Örnek: data içinde "<span class='result'>çeviri</span>" şeklinde bir yapı varsa
        # Bu örnekte basitçe "Çeviri bulunamadı" döndürüyoruz
        # Gerçek uygulamada scraping yapacak kod eklenmelidir
        result = "API çevirisi"
        
    except Exception as e:
        print(f"Çeviri API hatası: {str(e)}")
        result = "Çeviri bulunamadı"
    
    # Önbelleğe ekle ve döndür
    translation_cache[cache_key] = result
    return result 