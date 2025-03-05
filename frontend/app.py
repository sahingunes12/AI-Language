import streamlit as st
import requests
import json
import random
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import pandas as pd

# Set API endpoint
API_URL = "http://localhost:8000/api"  # FastAPI endpoint

# Session state for authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.access_token = None
    st.session_state.has_profile = False

# Title and description
st.title("Dil Öğrenme Uygulaması")

# Motivasyon Mesajları
def get_motivation_message(purpose, minutes):
    messages = {
        "konuşma": [
            f"Bugün {minutes} dakika konuşma pratiği yap!",
            f"Bugün yeni öğrendiğin kelimeleri kullanarak {minutes//2} dakika konuş!",
            f"Ayna karşısında {minutes} dakika konuş!"
        ],
        "yazma": [
            f"Bugün öğrendiğin konuyla ilgili {minutes} dakika yazı yaz!",
            f"Günlük tutarak {minutes} dakika yazı pratiği yap!",
            f"Bir arkadaşına {minutes//2} dakika boyunca mesaj yaz!"
        ],
        "dinleme": [
            f"Bugün {minutes} dakika podcast dinle!",
            f"Yabancı bir şarkıyı {minutes} dakika boyunca dinle ve anlamaya çalış!",
            f"Yabancı bir video izleyerek {minutes} dakika dinleme pratiği yap!"
        ],
        "okuma": [
            f"Bugün {minutes} dakika kitap oku!",
            f"Yabancı bir blog yazısı okuyarak {minutes} dakika geçir!",
            f"Yabancı haber sitelerinde {minutes} dakika geçir!"
        ]
    }
    
    purpose = purpose.lower()
    if purpose in messages:
        return random.choice(messages[purpose])
    return f"Bugün {minutes} dakika dil pratiği yap!"

# Login and registration page
def login_page():
    st.header("Giriş & Kayıt")
    
    tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
    
    with tab1:
        # Login form
        with st.form("login_form"):
            st.subheader("Giriş Yap")
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            login_button = st.form_submit_button("Giriş Yap")
            
            if login_button and username and password:
                try:
                    response = requests.post(
                        f"{API_URL}/login",
                        json={"username": username, "password": password}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.logged_in = True
                        st.session_state.username = data["username"]
                        st.session_state.access_token = data["access_token"]
                        st.success("Giriş başarılı! Ana sayfaya yönlendiriliyorsunuz...")
                        st.experimental_rerun()
                    else:
                        st.error("Geçersiz kullanıcı adı veya şifre.")
                except Exception as e:
                    st.error(f"Bağlantı hatası: {str(e)}")
                    st.info("Backend sunucusunun çalıştığından emin olun.")
    
    with tab2:
        # Registration form
        with st.form("registration_form"):
            st.subheader("Kayıt Ol")
            email = st.text_input("E-posta")
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")
            confirm_password = st.text_input("Şifreyi Tekrarla", type="password")
            register_button = st.form_submit_button("Kayıt Ol")
            
            if register_button:
                if not email or not new_username or not new_password:
                    st.error("Tüm alanları doldurun.")
                elif new_password != confirm_password:
                    st.error("Şifreler eşleşmiyor.")
                else:
                    try:
                        payload = {"email": email, "username": new_username, "password": new_password}
                        
                        response = requests.post(
                            f"{API_URL}/register",
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
                        else:
                            data = response.json()
                            st.error(f"Kayıt hatası: {data.get('detail', 'Bilinmeyen hata')}")
                    except Exception as e:
                        st.error(f"Bağlantı hatası: {str(e)}")
                        st.info("Backend sunucusunun çalıştığından emin olun.")

# Profil oluşturma sayfası
def create_profile_page():
    st.header("Profil Oluştur")
    st.write("Dil öğrenme hedeflerinizi belirleyin")
    
    # Profil oluşturmayı geç butonu
    if st.button("Şimdilik Profili Atla"):
        st.session_state.has_profile = True
        st.info("Profil oluşturmayı atladınız. İstediğiniz zaman 'Profil' sayfasından profilinizi oluşturabilirsiniz.")
        st.experimental_rerun()
    
    with st.form("profile_form"):
        learning_purpose = st.selectbox(
            "Dil öğrenme amacınız nedir?",
            options=["Konuşma", "Yazma", "Dinleme", "Okuma", "Gramer Öğrenme", "Kelime Dağarcığı Geliştirme"]
        )
        
        daily_minutes = st.slider(
            "Günlük kaç dakika ayırabilirsiniz?",
            min_value=5,
            max_value=120,
            value=30,
            step=5
        )
        
        submit_button = st.form_submit_button("Profil Oluştur")
        
        if submit_button:
            try:
                response = requests.post(
                    f"{API_URL}/profile",
                    json={
                        "learning_purpose": learning_purpose,
                        "daily_minutes": daily_minutes
                    },
                    headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                )
                
                if response.status_code == 200:
                    st.session_state.has_profile = True
                    st.session_state.profile = response.json()  # Profil bilgilerini session'a kaydet
                    st.success("Profil başarıyla oluşturuldu!")
                    st.experimental_rerun()
                else:
                    st.error(f"Profil oluşturma hatası: {response.text}")
            except Exception as e:
                st.error(f"Bağlantı hatası: {str(e)}")
                st.info("Backend sunucusunun çalıştığından emin olun.")

# Grafik oluşturma fonksiyonu
def create_activity_chart(data, chart_type="bar"):
    plt.figure(figsize=(10, 6))
    
    # Sadece görselleştirilecek verileri filtrele
    filtered_data = {k: v for k, v in data.items() if k not in ["total", "daily_average"]}
    
    if chart_type == "bar":
        # Renk paleti
        colors = sns.color_palette("husl", len(filtered_data.keys()))
        
        # Sütun grafiği
        ax = sns.barplot(x=list(filtered_data.keys()), y=list(filtered_data.values()), palette=colors)
        plt.title("Aktivite Türlerine Göre Harcanan Süre (Dakika)", fontsize=16)
        plt.ylabel("Dakika", fontsize=12)
        plt.xlabel("Aktivite Türü", fontsize=12)
        
        # Değerleri sütunların üzerine yaz
        for i, v in enumerate(filtered_data.values()):
            ax.text(i, v + 2, str(v), ha='center', fontsize=10)
            
    elif chart_type == "pie":
        # Pasta grafiği
        plt.pie(filtered_data.values(), labels=filtered_data.keys(), autopct='%1.1f%%',
                startangle=90, shadow=True)
        plt.axis('equal')  # Dairesel görünüm
        plt.title("Aktivite Dağılımı", fontsize=16)
    
    # Grafiği bir resim olarak kaydet
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Resmi base64'e dönüştür
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    plt.close()
    
    return image_base64

# Main application
def main_app():
    # Kullanıcı profilini kontrol et
    if not st.session_state.has_profile:
        try:
            response = requests.get(
                f"{API_URL}/profile",
                headers={"Authorization": f"Bearer {st.session_state.access_token}"}
            )
            
            if response.status_code == 200:
                st.session_state.has_profile = True
                st.session_state.profile = response.json()
            elif response.status_code == 404:
                # Profil henüz oluşturulmamış, varsayılan profil oluştur
                st.session_state.profile = {
                    "id": 0,
                    "learning_purpose": "Genel",
                    "daily_minutes": 15,
                    "created_at": "Henüz profil oluşturulmadı"
                }
            
        except Exception as e:
            # Hata durumunda varsayılan profil oluştur
            st.session_state.profile = {
                "id": 0,
                "learning_purpose": "Genel",
                "daily_minutes": 15,
                "created_at": "Henüz profil oluşturulmadı"
            }
    
    # Profil oluşturulmuş mu kontrol et
    if not st.session_state.has_profile:
        create_profile_page()
        return
    
    # Sidebar with page navigation
    page = st.sidebar.radio(
        "Sayfalar",
        ["Ana Sayfa", "Profil", "Motivasyon", "İlerleme Takibi", "Okuma Pratiği", "Öğeler Listesi", "Yeni Öğe Ekle"]
    )
    
    # Show username and logout button in sidebar
    st.sidebar.write(f"Kullanıcı: {st.session_state.username}")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.access_token = None
        st.session_state.has_profile = False
        st.experimental_rerun()
    
    if page == "Ana Sayfa":
        st.header("Dil Öğrenme Ana Sayfası")
        st.write("Bu uygulama dil öğrenme hedeflerinizi takip etmenize yardımcı olur.")
        
        # Motivasyon mesajı göster
        try:
            profile = st.session_state.profile
            motivation = get_motivation_message(profile["learning_purpose"], profile["daily_minutes"])
            
            st.info(motivation)
            
            # Günün ilerleyişini göster
            st.subheader("Günlük Hedefiniz")
            st.write(f"Günlük {profile['daily_minutes']} dakika {profile['learning_purpose']} pratiği")
            
            # İlerleme çubuğu
            st.progress(0.3)  # İlerleme durumunu temsil eder (0.0 - 1.0 arası)
            st.caption("Bugün 9 dakika tamamladınız")
            
        except Exception as e:
            st.warning("Profil bilgilerinize erişilemedi. Lütfen daha sonra tekrar deneyin.")

    elif page == "Profil":
        st.header("Kullanıcı Profili")
        
        # Profil bilgisi kontrolü
        if st.session_state.profile["id"] == 0:
            # Profil henüz oluşturulmamış
            st.warning("Henüz bir profil oluşturmadınız. Lütfen profil bilgilerinizi doldurun.")
            
            with st.form("create_profile_form"):
                new_purpose = st.selectbox(
                    "Dil öğrenme amacınız nedir?",
                    options=["Konuşma", "Yazma", "Dinleme", "Okuma", "Gramer Öğrenme", "Kelime Dağarcığı Geliştirme"]
                )
                
                new_minutes = st.slider(
                    "Günlük kaç dakika ayırabilirsiniz?",
                    min_value=5,
                    max_value=120,
                    value=30,
                    step=5
                )
                
                create_button = st.form_submit_button("Profil Oluştur")
                
                if create_button:
                    try:
                        response = requests.post(
                            f"{API_URL}/profile",
                            json={
                                "learning_purpose": new_purpose,
                                "daily_minutes": new_minutes
                            },
                            headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                        )
                        
                        if response.status_code == 200:
                            st.session_state.has_profile = True
                            st.session_state.profile = response.json()
                            st.success("Profil başarıyla oluşturuldu!")
                            st.experimental_rerun()
                        else:
                            st.error(f"Profil oluşturma hatası: {response.text}")
                    except Exception as e:
                        st.error(f"Bağlantı hatası: {str(e)}")
            
            return
            
        # Profil var ise göster
        try:
            profile = st.session_state.profile
            
            # Kişisel profil kartı
            st.markdown(
                f"""
                <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="color: #1f77b4; margin-bottom: 10px;">{st.session_state.username} Profili</h3>
                    <p style="font-size: 16px;"><strong>Dil Öğrenme Amacı:</strong> {profile["learning_purpose"]}</p>
                    <p style="font-size: 16px;"><strong>Günlük Hedef:</strong> {profile["daily_minutes"]} dakika</p>
                    <p style="font-size: 14px; color: #666;">Profil Oluşturulma: {profile["created_at"]}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # İstatistikleri göster
            st.subheader("Öğrenme İstatistikleri")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Çalışma", "12 saat")
            with col2:
                st.metric("Haftalık Çalışma", "3.5 saat", delta="↑ %20")
            with col3:
                st.metric("Başarı Oranı", "%75", delta="↑ %5")
            
            # İlerleme grafikleri
            st.subheader("Haftalık İlerleme")
            progress_data = {"Pazartesi": 0.8, "Salı": 1.0, "Çarşamba": 0.6, "Perşembe": 0.3, "Cuma": 0.0, "Cumartesi": 0.0, "Pazar": 0.0}
            
            for day, progress in progress_data.items():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.write(f"{day}:")
                with col2:
                    st.progress(progress)
            
            # Profil güncelleme butonu
            if st.button("Profili Güncelle"):
                with st.form("update_profile_form"):
                    purpose_options = ["Konuşma", "Yazma", "Dinleme", "Okuma", "Gramer Öğrenme", "Kelime Dağarcığı Geliştirme"]
                    current_purpose = profile["learning_purpose"]
                    
                    # Mevcut amacın indeksini bul
                    try:
                        purpose_index = [p.lower() for p in purpose_options].index(current_purpose.lower())
                    except ValueError:
                        purpose_index = 0
                    
                    new_purpose = st.selectbox(
                        "Dil öğrenme amacınız nedir?",
                        options=purpose_options,
                        index=purpose_index
                    )
                    
                    new_minutes = st.slider(
                        "Günlük kaç dakika ayırabilirsiniz?",
                        min_value=5,
                        max_value=120,
                        value=profile["daily_minutes"],
                        step=5
                    )
                    
                    update_button = st.form_submit_button("Güncelle")
                    
                    if update_button:
                        try:
                            update_response = requests.post(
                                f"{API_URL}/profile",
                                json={
                                    "learning_purpose": new_purpose,
                                    "daily_minutes": new_minutes
                                },
                                headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                            )
                            
                            if update_response.status_code == 200:
                                st.session_state.profile = update_response.json()
                                st.success("Profil başarıyla güncellendi!")
                                st.experimental_rerun()
                            else:
                                st.error(f"Profil güncelleme hatası: {update_response.text}")
                        except Exception as e:
                            st.error(f"Bağlantı hatası: {str(e)}")
            
            # Öğrenme tavsiyeleri
            st.subheader("Öğrenme Tavsiyeleri")
            
            purpose = profile["learning_purpose"].lower()
            if purpose == "konuşma":
                tips = [
                    "Günlük 10 dakika sesli okuma yaparak telaffuzunuzu geliştirebilirsiniz.",
                    "10 kelimeyi bulundugunuz seviyeye göre temel fiillerle birlikte kisa cümleler halinde yazın.",
                    "Kendinizi tanıtan kısa bir konuşma hazırlayın ve her gün tekrar edin.",
                    "Dil değişim arkadaşı bularak haftada bir canli olarak konusun veya yazisin."
                ]
            elif purpose == "yazma":
                tips = [
                    "Her gün en az 5 cümle yazarak günlük tutun.",
                    "Öğrendiğiniz yeni kelimeleri kullanarak kısa hikayeler yazın.",
                    "Dil öğrenme forumlarında yazarak pratik yapın."
                ]
            elif purpose == "dinleme":
                tips = [
                    "Yabancı dilde müzik dinleyin ve şarkı sözlerini anlamaya çalışın.",
                    "Podcast'leri önce altyazılı, sonra altyazısız dinleyin.",
                    "Kısa diyalogları tekrar tekrar dinleyerek kalıpları öğrenin."
                ]
            elif purpose == "okuma":
                tips = [
                    "Seviyenize uygun kısa hikayeler okuyun.",
                    "Görsel sözlükler kullanarak kelime dağarcığınızı geliştirin.",
                    "Gazete makalelerini çeviri yardımıyla okuyun."
                ]
            elif purpose == "gramer öğrenme":
                tips = [
                    "Her gün bir gramer kuralı seçip üzerinde çalışın.",
                    "Öğrendiğiniz kuralları kullanarak cümleler yazın.",
                    "Gramer alıştırma uygulamaları kullanarak pratik yapın."
                ]
            elif purpose == "kelime dağarcığı geliştirme":
                tips = [
                    "Kelime kartları oluşturun ve her gün gözden geçirin.",
                    "Kelimeleri kategorilere ayırarak öğrenin.",
                    "Öğrendiğiniz kelimeleri günlük konuşmada kullanmaya çalışın."
                ]
            else:
                tips = [
                    "Kendinize uygun bir öğrenme planı oluşturun.",
                    "Düzenli tekrar yaparak öğrendiklerinizi pekiştirin.",
                    "Dil öğrenmeyi günlük rutininize dahil edin."
                ]
            
            for tip in tips:
                st.markdown(f"- {tip}")
                
        except Exception as e:
            st.error(f"Profil bilgileri gösterilemedi: {str(e)}")
            st.button("Yeniden Dene", on_click=st.experimental_rerun)

    elif page == "Motivasyon":
        st.header("Günlük Motivasyon")
        
        # Profil kontrolü
        if "profile" not in st.session_state or st.session_state.profile["id"] == 0:
            st.warning("Henüz bir profil oluşturmadınız. Profil sayfasından profilinizi oluşturarak kişiselleştirilmiş motivasyon mesajları alabilirsiniz.")
            
            # Varsayılan motivasyon mesajları
            st.markdown(
                """
                <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="color: #1f77b4; margin-bottom: 10px;">Günün Mesajı</h3>
                    <p style="font-size: 18px; font-weight: bold;">Bugün yeni bir dil öğrenmeye başlamak için mükemmel bir gün!</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown("### Genel İpuçları")
            st.markdown("- Her gün en az 15 dakika dil öğrenmeye zaman ayırın")
            st.markdown("- Öğrendiklerinizi düzenli olarak tekrar edin")
            st.markdown("- Dil öğrenmeyi eğlenceli hale getirin")
            
            return
        
        try:
            profile = st.session_state.profile
            
            # Tarih ve gün bilgisi
            now = datetime.now()
            st.subheader(f"{now.strftime('%d %B %Y')}")
            
            # Motivasyon mesajı
            motivation = get_motivation_message(profile["learning_purpose"], profile["daily_minutes"])
            
            # Görsel bir motivasyon kartı
            st.markdown(
                f"""
                <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="color: #1f77b4; margin-bottom: 10px;">Günün Hedefi</h3>
                    <p style="font-size: 18px; font-weight: bold;">{motivation}</p>
                    <p style="font-size: 14px; margin-top: 10px;">Hedefiniz: Günde {profile["daily_minutes"]} dakika {profile["learning_purpose"]} çalışması</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Motivasyon alıntıları
            quotes = [
                "Bir dil, bir insan. İki dil, iki insan. - Türk Atasözü",
                "Yeni bir dil öğrenmek, yeni bir dünya keşfetmektir. - Frank Smith",
                "Bir dil öğrenmek asla geç değildir. - Anonymous",
                "Dil öğrenmek, beyniniz için en iyi egzersizdir. - Anonymous",
                "Pratik mükemmelleştirir. - Latin Atasözü"
            ]
            
            st.markdown("### Günün Alıntısı")
            st.markdown(f"> *{random.choice(quotes)}*")
            
            # İlerleme durumu
            st.subheader("Haftalık İlerlemeniz")
            week_data = {"Pazartesi": 0.8, "Salı": 1.0, "Çarşamba": 0.6, "Perşembe": 0.3, "Cuma": 0.0, "Cumartesi": 0.0, "Pazar": 0.0}
            
            for day, progress in week_data.items():
                st.write(f"{day}:")
                st.progress(progress)
            
            # İpuçları ve tavsiyeler
            st.subheader("Bugün İçin İpuçları")
            if profile["learning_purpose"].lower() == "konuşma":
                st.markdown("- Günlük konuşma kalıplarını tekrarlayın")
                st.markdown("- Ayna karşısında pratik yapın")
                st.markdown("- Sesli düşünmeye çalışın")
            elif profile["learning_purpose"].lower() == "yazma":
                st.markdown("- Günlük birkaç cümle yazın")
                st.markdown("- Yeni öğrendiğiniz kelimeleri kullanın")
                st.markdown("- Yazdıklarınızı sesli okuyun")
            elif profile["learning_purpose"].lower() == "dinleme":
                st.markdown("- Kısa diyalogları tekrar tekrar dinleyin")
                st.markdown("- Altyazılı video izleyin")
                st.markdown("- Anlamadığınız seslere odaklanın")
            elif profile["learning_purpose"].lower() == "okuma":
                st.markdown("- Basit metinlerle başlayın")
                st.markdown("- Bilmediğiniz kelimeleri not alın")
                st.markdown("- Sesli okuma yapın")
            elif profile["learning_purpose"].lower() == "gramer öğrenme":
                st.markdown("- Bir kural seçip cümleler kurun")
                st.markdown("- Gramer alıştırmaları çözün")
                st.markdown("- Öğrendiğiniz kuralları tekrar edin")
            elif profile["learning_purpose"].lower() == "kelime dağarcığı geliştirme":
                st.markdown("- Konulara göre kelime listeleri oluşturun")
                st.markdown("- Resimli kelime kartları hazırlayın")
                st.markdown("- Kelimeleri cümle içinde kullanın")
            
        except Exception as e:
            st.warning(f"Motivasyon içeriği oluşturulurken bir hata oluştu: {str(e)}")
            st.button("Yeniden Dene", on_click=st.experimental_rerun)

    elif page == "İlerleme Takibi":
        st.header("Dil Öğrenme İlerleme Takibi")
        
        # Sekmelere ayır
        tab1, tab2, tab3 = st.tabs(["Günlük Aktivite", "İlerleme Analizi", "Tavsiyeler"])
        
        with tab1:
            st.subheader("Bugün Ne Öğrendin?")
            
            with st.form("activity_form"):
                activity_type = st.selectbox(
                    "Hangi aktiviteyi tamamladın?",
                    options=["Konuşma", "Yazma", "Dinleme", "Okuma", "Gramer Öğrenme", "Kelime Dağarcığı Geliştirme"]
                )
                
                duration = st.slider(
                    "Kaç dakika çalıştın?",
                    min_value=5,
                    max_value=120,
                    value=15,
                    step=5
                )
                
                notes = st.text_area(
                    "Notlar (İsteğe bağlı)",
                    placeholder="Bugün ne öğrendin? Zorluklar nelerdi?"
                )
                
                submit_activity = st.form_submit_button("Aktiviteyi Kaydet")
                
                if submit_activity:
                    try:
                        response = requests.post(
                            f"{API_URL}/activities",
                            json={
                                "activity_type": activity_type,
                                "duration": duration,
                                "notes": notes
                            },
                            headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                        )
                        
                        if response.status_code == 200:
                            st.success("Aktivite başarıyla kaydedildi!")
                            st.balloons()
                        else:
                            st.error(f"Aktivite kaydedilemedi: {response.text}")
                    except Exception as e:
                        st.error(f"Bağlantı hatası: {str(e)}")
            
            # Son aktiviteleri göster
            st.subheader("Son Aktiviteler")
            
            try:
                activities_response = requests.get(
                    f"{API_URL}/activities",
                    headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                )
                
                if activities_response.status_code == 200:
                    activities = activities_response.json()
                    
                    if activities:
                        for activity in activities[:5]:  # Son 5 aktivite
                            with st.expander(f"{activity['activity_type']} - {activity['completed_at']}"):
                                st.write(f"Süre: {activity['duration']} dakika")
                                if activity['notes']:
                                    st.write(f"Notlar: {activity['notes']}")
                    else:
                        st.info("Henüz kaydedilmiş aktiviteniz bulunmamaktadır.")
                else:
                    st.error("Aktiviteler alınamadı.")
            except Exception as e:
                st.error(f"Aktivite verisi alınamadı: {str(e)}")
        
        with tab2:
            st.subheader("İlerleme Analizi")
            
            # Zaman aralığı seçimi
            period = st.radio(
                "Analiz Periyodu:",
                options=["Haftalık", "Aylık", "Yıllık"],
                horizontal=True
            )
            
            period_map = {
                "Haftalık": "week",
                "Aylık": "month",
                "Yıllık": "year"
            }
            
            try:
                summary_response = requests.get(
                    f"{API_URL}/activities/summary",
                    params={"period": period_map[period]},
                    headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                )
                
                if summary_response.status_code == 200:
                    summary_data = summary_response.json()
                    
                    if summary_data["summary"]["total"] > 0:
                        # Metrikler
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Toplam Çalışma", f"{summary_data['summary']['total']} dk")
                        with col2:
                            st.metric("Günlük Ortalama", f"{summary_data['summary']['daily_average']:.1f} dk")
                        with col3:
                            if "profile" in st.session_state:
                                target = st.session_state.profile.get("daily_minutes", 30)
                                percentage = (summary_data['summary']['daily_average'] / target) * 100
                                st.metric("Hedefe Ulaşma", f"%{percentage:.1f}")
                        
                        # Grafik türü seçimi
                        chart_type = st.radio(
                            "Grafik Türü:",
                            options=["Sütun Grafiği", "Pasta Grafiği"],
                            horizontal=True
                        )
                        
                        # Grafiği oluştur
                        if chart_type == "Sütun Grafiği":
                            chart_img = create_activity_chart(summary_data["summary"], "bar")
                        else:
                            chart_img = create_activity_chart(summary_data["summary"], "pie")
                        
                        # Grafiği göster
                        st.markdown(f'<img src="data:image/png;base64,{chart_img}" style="width: 100%">', unsafe_allow_html=True)
                        
                        # Aktivite dağılımı tablosu
                        st.subheader("Aktivite Detayları")
                        
                        activity_data = {k: v for k, v in summary_data["summary"].items() 
                                         if k not in ["total", "daily_average"]}
                        
                        df = pd.DataFrame({
                            "Aktivite Türü": activity_data.keys(),
                            "Toplam Süre (dk)": activity_data.values(),
                            "Yüzde (%)": [
                                f"{(v / summary_data['summary']['total']) * 100:.1f}%" 
                                for v in activity_data.values()
                            ]
                        })
                        
                        st.dataframe(df, use_container_width=True)
                        
                    else:
                        st.info(f"Seçilen {period.lower()} periyodunda henüz aktivite kaydınız bulunmamaktadır.")
                        st.markdown("İlerlemenizi görmek için aktivitelerinizi kaydetmeye başlayın!")
                else:
                    st.error("Özet verisi alınamadı.")
            except Exception as e:
                st.error(f"İlerleme verisi alınamadı: {str(e)}")
        
        with tab3:
            st.subheader("Akıllı Tavsiyeler")
            
            try:
                # Özet verisini kullan
                if 'summary_data' not in locals():
                    summary_response = requests.get(
                        f"{API_URL}/activities/summary",
                        params={"period": "week"},
                        headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                    )
                    
                    if summary_response.status_code == 200:
                        summary_data = summary_response.json()
                    else:
                        st.error("Tavsiyeler için veri alınamadı.")
                        st.stop()
                
                # Tavsiyeleri göster
                if "recommendations" in summary_data and summary_data["recommendations"]:
                    for i, recommendation in enumerate(summary_data["recommendations"]):
                        st.markdown(f"**{i+1}. {recommendation}**")
                else:
                    # Varsayılan tavsiyeler
                    st.markdown("**1. Her gün düzenli olarak çalışın, kısa süreli bile olsa süreklilik önemlidir.**")
                    st.markdown("**2. Farklı beceri alanlarında (konuşma, dinleme, okuma, yazma) dengeli çalışın.**")
                    st.markdown("**3. Öğrendiklerinizi günlük hayatınızda kullanmaya çalışın.**")
                
                # Gelişim ipuçları
                st.subheader("Dil Öğrenme İpuçları")
                
                tips = [
                    "Yabancı dizileri altyazılı izleyin ve tekrar eden ifadeleri not alın.",
                    "Sevdiğiniz şarkıların sözlerini yazıp anlamaya çalışın.",
                    "Günlük rutininizi yabancı dilde sesli olarak anlatmayı deneyin.",
                    "Basit günlük notları öğrendiğiniz dilde tutun.",
                    "Kelime öğrenirken görsellerle ilişkilendirin, hatırlamanız kolaylaşır.",
                    "Dil değişim uygulamalarından bir arkadaş edinin ve düzenli pratik yapın.",
                    "Kelimeleri bağlam içinde öğrenin ve cümle içinde kullanın.",
                    "Kendi seviyenize uygun podcast'ler bulun ve düzenli dinleyin."
                ]
                
                # Rastgele 3 ipucu göster
                import random
                selected_tips = random.sample(tips, 3)
                
                for tip in selected_tips:
                    st.markdown(f"- {tip}")
                    
            except Exception as e:
                st.error(f"Tavsiyeler oluşturulurken hata oluştu: {str(e)}")

    elif page == "Öğeler Listesi":
        st.header("Öğeler")
        
        # Fetch items from API
        try:
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"} if st.session_state.access_token else {}
            response = requests.get(f"{API_URL}/items", headers=headers)
            
            if response.status_code == 200:
                items = response.json()
                if items:
                    for item in items:
                        with st.expander(f"{item['name']}"):
                            st.write(f"ID: {item['id']}")
                            st.write(f"Açıklama: {item['description']}")
                else:
                    st.info("Henüz hiç öğe bulunmamaktadır.")
            else:
                st.error(f"API'den veri alınamadı. Hata kodu: {response.status_code}")
        except Exception as e:
            st.error(f"Bağlantı hatası: {str(e)}")
            st.info("Backend sunucusunun çalıştığından emin olun.")

    elif page == "Yeni Öğe Ekle":
        st.header("Yeni Öğe Ekle")
        
        with st.form("item_form"):
            name = st.text_input("Öğe Adı")
            description = st.text_area("Açıklama")
            submit = st.form_submit_button("Ekle")
            
            if submit and name:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.access_token}"} if st.session_state.access_token else {}
                    response = requests.post(
                        f"{API_URL}/items",
                        json={"name": name, "description": description},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        st.success("Öğe başarıyla eklendi!")
                        st.json(response.json())
                    else:
                        st.error(f"Öğe eklenemedi. Hata kodu: {response.status_code}")
                except Exception as e:
                    st.error(f"Bağlantı hatası: {str(e)}")
                    st.info("Backend sunucusunun çalıştığından emin olun.")

    elif page == "Okuma Pratiği":
        reading_practice_page()

# Okuma pratiği sayfasını güncelle
def reading_practice_page():
    st.header("AI Destekli Okuma Pratiği")
    
    # Seviye ve konu seçimi
    col1, col2 = st.columns(2)
    
    with col1:
        level = st.selectbox(
            "Dil Seviyeniz:",
            options=["A1 (Başlangıç)", "A2 (Temel)", "B1 (Orta-Altı)", "B2 (Orta)", "C1 (İleri)", "C2 (Ustalaşmış)"],
            index=2  # Varsayılan olarak B1
        )
    
    level_map = {
        "A1 (Başlangıç)": "a1",
        "A2 (Temel)": "a2",
        "B1 (Orta-Altı)": "b1",
        "B2 (Orta)": "b2",
        "C1 (İleri)": "c1",
        "C2 (Ustalaşmış)": "c2"
    }
    
    with col2:
        topic = st.text_input("İstediğiniz konu (boş bırakırsanız rastgele seçilir):")
    
    # Metin getir butonu
    if st.button("Okuma Metni Getir"):
        with st.spinner("Metin getiriliyor..."):
            try:
                response = requests.get(
                    f"{API_URL}/reading/text",
                    params={"level": level_map[level], "topic": topic if topic else None},
                    headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                )
                
                if response.status_code == 200:
                    reading_data = response.json()
                    st.session_state.reading_data = reading_data
                    st.success("Metin başarıyla getirildi!")
                    st.experimental_rerun()
                else:
                    st.error(f"Metin getirilemedi: {response.text}")
            except Exception as e:
                st.error(f"Bağlantı hatası: {str(e)}")
    
    # Metin varsa göster
    if "reading_data" in st.session_state:
        data = st.session_state.reading_data
        
        st.subheader(data["title"])
        st.markdown(f"**Seviye:** {level}")
        
        # Kelime anlamlarını görmek için işaretlenen kelimeleri takip et
        if "marked_words" not in st.session_state:
            st.session_state.marked_words = set()
        
        # Metni göster
        st.markdown("### Metin")
        text = data["text"]
        
        # Kelime anlamlarını göster
        st.markdown("### Öğrenilecek Kelimeler")
        
        # Kelimeler ve fiiller için sekme oluştur
        if data["unknown_words"]:
            word_tab1, word_tab2 = st.tabs(["Tüm Kelimeler", "Fiiller ve İsimler"])
            
            with word_tab1:
                word_cols = st.columns(4)
                for i, word in enumerate(data["unknown_words"]):
                    col_index = i % 4
                    with word_cols[col_index]:
                        if st.button(word, key=f"word_{word}"):
                            st.session_state.marked_words.add(word)
                            # Otomatik olarak anlamı göster
                            meaning = data['word_meanings'].get(word, 'Anlam bulunamadı')
                            st.success(f"**{word}**: {meaning}")
            
            with word_tab2:
                verb_col, noun_col = st.columns(2)
                
                with verb_col:
                    st.subheader("Fiiller")
                    for verb in data.get("verbs", []):
                        if st.button(verb, key=f"verb_{verb}"):
                            st.session_state.marked_words.add(verb)
                            meaning = data['word_meanings'].get(verb, 'Anlam bulunamadı')
                            st.success(f"**{verb}**: {meaning}")
                
                with noun_col:
                    st.subheader("İsimler/Sıfatlar")
                    for noun in data.get("nouns", []):
                        if st.button(noun, key=f"noun_{noun}"):
                            st.session_state.marked_words.add(noun)
                            meaning = data['word_meanings'].get(noun, 'Anlam bulunamadı')
                            st.success(f"**{noun}**: {meaning}")
            
            # İşaretlenen kelimelerin anlamlarını göster
            if st.session_state.marked_words:
                st.markdown("### Öğrenilen Kelimeler")
                
                for word in st.session_state.marked_words:
                    st.markdown(f"**{word}**: {data['word_meanings'].get(word, 'Anlam bulunamadı')}")
                    
                # Kelime listesini temizle butonu
                if st.button("Kelime Listesini Temizle"):
                    st.session_state.marked_words = set()
                    st.experimental_rerun()
        else:
            st.info("Bu metinde öğrenilecek kelime tespit edilmedi.")
        
        # Metni göster
        st.markdown("### Tam Metin")
        st.write(text)
        
        # Metni kopyala butonu
        st.download_button(
            label="Metni Kopyala",
            data=text,
            file_name=f"{data['title']}.txt",
            mime="text/plain"
        )
        
        # Özeti göster
        st.markdown("### Metnin Özeti")
        st.write(data["summary"])
        
        # Dil algılama alanı
        st.markdown("### Dil Pratiği")
        st.markdown("Aşağıdaki alana kendi çevirinizi yazın. Dilinizi otomatik olarak algılayacağız.")
        
        user_text = st.text_area("Çevirinizi buraya yazın:", height=150)
        
        if user_text:
            if st.button("Dili Algıla"):
                try:
                    lang_response = requests.post(
                        f"{API_URL}/reading/detect-language",
                        json={"text": user_text},
                        headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                    )
                    
                    if lang_response.status_code == 200:
                        lang_data = lang_response.json()
                        
                        lang_map = {
                            "es": "İspanyolca",
                            "en": "İngilizce",
                            "tr": "Türkçe",
                            "de": "Almanca",
                            "fr": "Fransızca",
                            "it": "İtalyanca",
                            "pt": "Portekizce",
                            "ru": "Rusça",
                            "ja": "Japonca",
                            "zh-cn": "Çince",
                            "ko": "Korece",
                            "ar": "Arapça"
                        }
                        
                        detected_lang = lang_map.get(lang_data["language"], lang_data["language"])
                        
                        if lang_data["language"] == "es":
                            st.success(f"Tebrikler! Metniniz {detected_lang} olarak algılandı.")
                        else:
                            st.warning(f"Metniniz {detected_lang} olarak algılandı. İspanyolca yazmaya çalışın!")
                    else:
                        st.error(f"Dil algılanamadı: {lang_response.text}")
                except Exception as e:
                    st.error(f"Bağlantı hatası: {str(e)}")
        
        # Wikipedia bağlantısı
        st.markdown("### Kaynak")
        st.markdown(f"Bu metin [Wikipedia]({data['url']}) kaynağından alınmıştır.")

# Main flow based on login status
if st.session_state.logged_in:
    main_app()
else:
    login_page() 