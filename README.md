# 🚗 Bulanık Mantık Tabanlı Yakıt Optimizasyon Platformu

Bu proje, farklı motor tiplerine sahip araçlar için yakıt tüketimini optimize etmek ve sürücüye en verimli vites/devir kullanımını tavsiye etmek amacıyla geliştirilmiş, **Bulanık Mantık (Fuzzy Logic)** tabanlı modüler bir simülasyon platformudur.

## 💡 Projenin Vizyonu

Günümüz araçlarında ECU (Elektronik Kontrol Ünitesi) bu işlemleri otomatik yapsa da, manuel vitesli araçlarda verimlilik tamamen sürücü kararlarına bağlıdır. Bu çalışma; bir mühendislik yaklaşımıyla, öznel sürüş dinamiklerini (devir, gaz pedal baskısı, yol eğimi) matematiksel bir model olan Bulanık Mantık ile sayısallaştırır.

## 🏗️ Modüler Mimari

Proje, sürdürülebilir yazılım prensiplerine uygun olarak 3 ana modülden oluşmaktadır:

* **`main.py`**: Streamlit tabanlı interaktif kullanıcı arayüzü (Dashboard).
* **`fuzzy_engine.py`**: Mamdani çıkarım yöntemini kullanan bulanık mantık karar mekanizması.
* **`engine_configs.py`**: Farklı motor tiplerinin (1.3 Dizel, 1.6 Atmosferik, 1.0 Turbo) tork ve devir karakteristiklerini barındıran parametrik veri seti.

## ✨ Teknik Özellikler

* **Dinamik Motor Profilleri:** Seçilen araca göre üyelik fonksiyonları (Membership Functions) otomatik olarak yeniden ölçeklenir.
* **Gelişmiş Kural Tabanı:** Kural boşlukları (rule gaps) minimize edilmiş, 10'dan fazla kompleks senaryoyu kapsayan karar matrisi.
* **Akademik Görselleştirme:** Karar anında arka planda gerçekleşen bulanık kesişim grafiklerini (Matplotlib) gerçek zamanlı sunabilme.
* **Hata Yakalama (Robustness):** Beklenmedik veri girişlerinde sistemin çökmesini engelleyen `try-except` ve `fallback` mekanizmaları.

## 🛠️ Kurulum

1. Repoyu klonlayın:
   ```bash
   git clone [https://github.com/KULLANICI_ADIN/fuzzy-logic-fuel-optimizer.git](https://github.com/KULLANICI_ADIN/fuzzy-logic-fuel-optimizer.git)
   cd fuzzy-logic-fuel-optimizer
