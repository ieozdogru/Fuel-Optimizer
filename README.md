# Bulanık Mantık Tabanlı Yakıt Optimizasyon Platformu

Bu proje, farklı motor tiplerine sahip araçlar için yakıt tüketimini optimize etmek ve sürücüye en verimli vites/devir kullanımını tavsiye etmek amacıyla geliştirilmiş, **Bulanık Mantık** tabanlı modüler bir simülasyon platformudur.

## Projenin Vizyonu

Günümüz araçlarında ECU (Elektronik Kontrol Ünitesi) bu işlemleri otomatik yapsa da, manuel vitesli araçlarda verimlilik tamamen sürücü kararlarına bağlıdır. Bu çalışma; bir mühendislik yaklaşımıyla, öznel sürüş dinamiklerini (devir, gaz pedal baskısı, yol eğimi) matematiksel bir model olan Bulanık Mantık ile sayısallaştırır.

## Modüler mimari

Çekirdek modüller:

* **`main.py`** — Streamlit arayüzü (Dashboard, Diagnostics, Mamdani vs Sugeno, Trajectory sekmeleri).
* **`fuzzy_engine.py`** — Mamdani (scikit-fuzzy, centroid) ve aynı kural tabanıyla **sıfırıncı derece Sugeno** (singleton + ağırlıklı ortalama; taşınabilirlik için elle uygulanmış).
* **`engine_configs.py`** — Motor profilleri (RPM aralıkları).

Destekleyici modüller:

* **`diagnostics.py`** — RPM × gaz ızgara taraması, başarı oranı, Mamdani–Sugeno karşılaştırması.
* **`trajectory.py`** — Sentetik sürüş döngüsü ve toplu değerlendirme.
* **`baselines.py`** — Bulanık olmayan kaba (crisp) kıyaslama.

Akademik özet: `docs/TECHNICAL.md`.

## Teknik özellikler

* Dinamik motor profillerine göre RPM üyelik fonksiyonları.
* Etiketli 16 kural; panelde **kural ateşleme güçleri** ve **girdi üyelikleri** tabloları.
* **Plotly** ile etkileşimli ısı haritaları; **Matplotlib** ile çıkış üyelikleri.
* **pytest** + GitHub Actions CI.

## Kurulum (yerel)

Python 3.10+ önerilir. Sanal ortam:

```bash
git clone https://github.com/<org>/Fuel-Optimizer.git
cd Fuel-Optimizer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run main.py
```

Testler:

```bash
pytest -q
```
