import streamlit as st
from fuzzy_engine import FuzzyEngine
from engine_configs import ENGINE_CONFIGS

# 1. Sayfa Temel Ayarları
st.set_page_config(page_title="Çoklu Araç Telemetri", page_icon="🏎️", layout="wide")

@st.cache_resource
def get_engine(car_name):
    """
    Seçilen araç adına göre ENGINE_CONFIGS'ten verileri çeker ve 
    FuzzyEngine nesnesini bellekte tutarak (cache) sisteme kazandırır.
    Araç değişikliğinde nesne yeniden oluşturulur (dinamik yapı).
    """
    config = ENGINE_CONFIGS[car_name]
    return FuzzyEngine(config)

def main():
    # 2. Üst Header / Başlık
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🏎️ Çoklu Araç Telemetri ve Optimizasyon Dashboard'u</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>Seçtiğiniz araç mimarisine göre akademik <b>Bulanık Mantık (Fuzzy Logic)</b> işlemi gerçekleştirilir.</p>", unsafe_allow_html=True)
    
    st.write("---")
    
    # 3. İki Sütunlu Profesyonel Arayüz Tasarımı
    col1, col2 = st.columns([1, 2], gap="large")
    
    # SOL SÜTUN: Araç Seçimi ve Sensör Kontrol Paneli
    with col1:
        st.subheader("🚙 Araç Kalibrasyon Seçimi")
        secilen_arac = st.selectbox("Lütfen Bir Araç Profili Seçiniz", list(ENGINE_CONFIGS.keys()))
        
        # Seçtiğimiz araca ait fuzzy nesnesi yaratılıyor
        engine = get_engine(secilen_arac)
        
        st.write("---")
        st.subheader("🎛️ Sensör Kontrol Paneli")
        st.info(f"Girilen değerler **{secilen_arac}** teknik devir sınırlarına göredir.")
        
        # Dinamik Slider Limitleri
        max_limit = engine.rpm_max
        ideal_start = engine.config['ideal_range'][0]
        
        val_devir = st.slider("Engine RPM (Motor Devri)", min_value=0, max_value=max_limit, value=int(ideal_start), step=10)
        val_gaz = st.slider("Throttle Position (Gaz Pedalı %)", min_value=0, max_value=100, value=40, step=1)
        val_egim = st.slider("Road Incline (Yol Eğimi Derecesi)", min_value=-20, max_value=20, value=0, step=1)
        
    # Arka planda otonom olarak aracı simüle et
    result = engine.evaluate(val_devir, val_gaz, val_egim)
    
    # SAĞ SÜTUN: Göstergeler ve Karar Çıktısı
    with col2:
        st.subheader("📊 Anlık Telemetri Metrikleri")
        
        # O anki verileri şık gösterge panelleri (metrics) ile sun
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Motor Devri", f"{val_devir} RPM")
        m_col2.metric("Gaz Pedalı", f"% {val_gaz}")
        m_col3.metric("Yol Eğimi", f"{val_egim} °")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🤖 Otonom Asistan Kararı")
        
        # Başarısızlık Yönetimi (Kural Boşlukları veya Hata Durumları)
        if not result['success']:
            if result.get('hata') == 'KeyError':
                st.warning("⚠️ **GÜVENLİK SİSTEMİ:** Seçilen sensör aralığı test edilen dinamik uzayın dışında. Güvenliğiniz için mevcut durumu koruyun.")
            else:
                st.error("⚠️ **HESAPLAMA HATASI:** Kapsam dışı sensör değeri.")
        
        # Başarılı Tahmin Reaksiyonları
        else:
            tavsiye = result['tavsiye']
            
            if tavsiye == 'VİTES BÜYÜT':
                st.success(f"## ⬆️ {tavsiye}\n**Araç Analizi:** Yüksek devir tespit edildi. Güç yeterli; daha ekonomik ve sessiz sürüş için üst vitese geçin.")
            elif tavsiye == 'VİTES KÜÇÜLT':
                st.error(f"## ⬇️ {tavsiye}\n**Araç Analizi:** Devir düşüklüğü / Rampa saptandı. Araç bayılmak üzere yığılmamak için bir alt vitese takıp çekişi toparlayın.")
            elif tavsiye == 'GAZDAN ÇEK':
                st.warning(f"## 🦶 {tavsiye}\n**Araç Analizi:** İvme yeterli veya yokuş aşağı rejiminde iniliyor. Ayağınızı gazdan tamamen çekerek (Fuel Cut-off) yakıt tüketimini 0.0'a düşürün.")
            else:
                st.info(f"## ➖ {tavsiye}\n**Araç Analizi:** Sensör telemetrisine göre vites/gaz oranınız optimum seviyede çalışıyor, sürüşü bozmayın.")
                
    st.write("---")
    
    # 4. Akademik Matematiksel Altyapı (Expander Görünümü)
    with st.expander("🔎 Matematiksel Çıktı ve Bulanık Durulaştırma Detayları", expanded=False):
        c1, c2 = st.columns([1, 2])
        skor_val = result['skor']
        
        with c1:
            st.markdown("### Kesinleştirme Skoru")
            st.markdown(f"<h1 style='color: #E67E22; font-size: 50px;'>{skor_val:.2f}</h1><p> / 100 Merkez Ağırlık Skoru</p>", unsafe_allow_html=True)
            st.markdown("**Bulanık Çıkarım Sistemi:** Mamdani\n\n**Durulaştırma Metodu:** Centroid (Sıklet Merkezi)")
            st.markdown("*Matematiksel fonksiyonlar seçtiğiniz araca ait devir limitleri üzerinden dinamik daraltılmış veya genişletilmiştir.*")
            
        with c2:
            st.markdown("### 📈 Kural Kesişim ve Alan Tarama Grafiği")
            if result['success']:
                # Engine objesinin plot fonsiyonuna skor geçiriyoruz, güvenli Matplotlib çizimi basılıyor
                fig = engine.plot_result(skor_val)
                st.pyplot(fig)
            else:
                st.info("Kural örtüşmesi olmadığı için Grafik Çizilemedi.")

if __name__ == '__main__':
    main()
